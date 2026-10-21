"""Resolve LeavePolicy rows and validate leave requests against JSON rules + ledger."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Employee, LeaveAccrualLedger, LeavePolicy


def calendar_days_inclusive(start: date, end: date) -> int:
    return (end - start).days + 1


def resolve_policy_for_employee(db: Session, employee: Employee) -> Optional[LeavePolicy]:
    if employee.department_id:
        p = (
            db.query(LeavePolicy)
            .filter(LeavePolicy.department_id == employee.department_id)
            .order_by(LeavePolicy.id.asc())
            .first()
        )
        if p:
            return p
    return (
        db.query(LeavePolicy)
        .filter(LeavePolicy.department_id.is_(None))
        .order_by(LeavePolicy.id.asc())
        .first()
    )


def _norm_leave_type(s: str) -> str:
    return (s or "").strip().lower()


def ledger_has_entries(db: Session, *, employee_id: int, leave_type: str) -> bool:
    lt = _norm_leave_type(leave_type)
    row = (
        db.query(LeaveAccrualLedger.id)
        .filter(
            LeaveAccrualLedger.employee_id == employee_id,
            func.lower(LeaveAccrualLedger.leave_type) == lt,
        )
        .first()
    )
    return row is not None


def latest_ledger_balance(db: Session, *, employee_id: int, leave_type: str) -> Optional[float]:
    lt = _norm_leave_type(leave_type)
    row = (
        db.query(LeaveAccrualLedger)
        .filter(
            LeaveAccrualLedger.employee_id == employee_id,
            func.lower(LeaveAccrualLedger.leave_type) == lt,
            LeaveAccrualLedger.balance_after.is_not(None),
        )
        .order_by(LeaveAccrualLedger.created_at.desc())
        .first()
    )
    return float(row.balance_after) if row else None


def validate_new_leave(
    db: Session,
    *,
    employee: Employee,
    leave_type: str,
    start: date,
    end: date,
) -> Optional[LeavePolicy]:
    """Raises HTTPException if rules violate; returns policy used (or None if no policy)."""
    policy = resolve_policy_for_employee(db, employee)
    if not policy:
        return None

    rules: dict[str, Any] = policy.rules or {}
    lt = leave_type.strip()

    allowed = rules.get("allowed_leave_types")
    if isinstance(allowed, list) and allowed:
        allowed_l = {_norm_leave_type(x) for x in allowed if isinstance(x, str)}
        if _norm_leave_type(lt) not in allowed_l:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Leave type {lt!r} is not allowed under policy {policy.name!r}.",
            )

    max_days = rules.get("max_consecutive_calendar_days")
    if max_days is not None:
        try:
            md = int(max_days)
        except (TypeError, ValueError):
            md = None
        if md is not None:
            span = calendar_days_inclusive(start, end)
            if span > md:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Leave spans {span} calendar days; maximum allowed is {md}.",
                )

    if rules.get("enforce_ledger"):
        if ledger_has_entries(db, employee_id=employee.id, leave_type=lt):
            hours_per_day = float(rules.get("hours_per_day") or 8)
            days = calendar_days_inclusive(start, end)
            need_hours = days * hours_per_day
            prev = latest_ledger_balance(db, employee_id=employee.id, leave_type=lt)
            base = float(prev) if prev is not None else 0.0
            if base + 1e-6 < need_hours:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Insufficient accrued balance for {lt} (need {need_hours} hours, have {base}).",
                )

    return policy


def apply_leave_approval_ledger(
    db: Session,
    *,
    employee_id: int,
    leave_type: str,
    start: date,
    end: date,
    policy: Optional[LeavePolicy],
    note: str = "leave approved",
) -> None:
    """Debit ledger when policy.enforce_ledger is true (same transaction as approval)."""
    if not policy:
        return
    rules = policy.rules or {}
    if not rules.get("enforce_ledger"):
        return
    hours_per_day = float(rules.get("hours_per_day") or 8)
    days = calendar_days_inclusive(start, end)
    delta_hours = -(days * hours_per_day)
    prev = latest_ledger_balance(db, employee_id=employee_id, leave_type=leave_type.strip())
    base = float(prev) if prev is not None else 0.0
    after = base + delta_hours
    db.add(
        LeaveAccrualLedger(
            employee_id=employee_id,
            leave_type=leave_type.strip(),
            hours_delta=delta_hours,
            balance_after=after,
            note=note[:500],
        )
    )
