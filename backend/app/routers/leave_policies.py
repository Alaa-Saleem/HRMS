"""Minimal leave policy + ledger read APIs (admin)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DbSession
from app.models import BlackoutDate, LeaveAccrualLedger, LeavePolicy, Role

router = APIRouter(prefix="/leave-policies", tags=["leave-policies"])


@router.get("")
def list_policies(db: DbSession, user: CurrentUser):
    if user.role != Role.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    rows = db.query(LeavePolicy).order_by(LeavePolicy.id.asc()).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "department_id": p.department_id,
            "rules": p.rules or {},
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in rows
    ]


@router.get("/blackouts")
def list_blackouts(db: DbSession, user: CurrentUser):
    if user.role != Role.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    rows = db.query(BlackoutDate).order_by(BlackoutDate.start_date.asc()).all()
    return [
        {
            "id": b.id,
            "start_date": b.start_date.isoformat(),
            "end_date": b.end_date.isoformat(),
            "label": b.label,
            "department_id": b.department_id,
        }
        for b in rows
    ]


@router.get("/ledger/{employee_id}")
def ledger_for_employee(db: DbSession, user: CurrentUser, employee_id: int):
    if user.role != Role.admin and user.id != employee_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    rows = (
        db.query(LeaveAccrualLedger)
        .filter(LeaveAccrualLedger.employee_id == employee_id)
        .order_by(LeaveAccrualLedger.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": r.id,
            "leave_type": r.leave_type,
            "hours_delta": r.hours_delta,
            "balance_after": r.balance_after,
            "note": r.note,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
