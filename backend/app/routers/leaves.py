from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from sqlalchemy import and_, or_

from app.audit import log_audit
from app.deps import CurrentUser, DbSession
from app.leave_policy_engine import (
    apply_leave_approval_ledger,
    resolve_policy_for_employee,
    validate_new_leave,
)
from app.models import BlackoutDate, Employee, LeaveRequest, LeaveStatus, Notification, Role
from app.notifications_dispatch import notify_leave_decision, notify_leave_new_request
from app.rbac import can_approve_leave
from app.schemas_http import LeaveCreate, LeaveStatusUpdate
from app.serialization import employee_to_frontend, leave_detail_string, leave_to_frontend

router = APIRouter(prefix="/leave-requests", tags=["leaves"])


def _dept(db):
    from app.models import Department

    return {d.id: d.name for d in db.query(Department).all()}


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_leave(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    body: LeaveCreate,
    background_tasks: BackgroundTasks,
):
    s = body.start
    ed = body.end
    if ed < s:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "End date cannot be before start date.")

    b = (
        db.query(BlackoutDate)
        .filter(
            or_(BlackoutDate.department_id.is_(None), BlackoutDate.department_id == user.department_id),
            and_(BlackoutDate.start_date <= ed, BlackoutDate.end_date >= s),
        )
        .first()
    )
    if b:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Leave overlaps blackout period: {b.label} ({b.start_date} – {b.end_date})",
        )

    validate_new_leave(db, employee=user, leave_type=body.type, start=s, end=ed)

    lr = LeaveRequest(
        employee_id=user.id,
        type=body.type,
        start_date=s,
        end_date=ed,
        reason=body.reason or "",
        status=LeaveStatus.pending,
    )
    db.add(lr)
    db.flush()

    days = (ed - s).days + 1
    mgr = db.get(Employee, user.manager_id) if user.manager_id else None
    dn = employee_to_frontend(user, _dept(db).get(user.department_id, ""))
    nm = (dn["first"] + " " + dn["last"]).strip()

    if mgr:
        db.add(
            Notification(
                target_id=mgr.id,
                type="leave",
                dot="orange",
                title="New Leave Request",
                text=f"{nm} requested {lr.type.lower()} ({days} day{'s' if days != 1 else ''}).",
            )
        )

    admins = db.query(Employee.id).filter(Employee.role == Role.admin).limit(10).all()
    for aid in admins:
        db.add(
            Notification(
                target_id=aid[0],
                type="leave",
                dot="orange",
                title="New Leave Request",
                text=f"{nm} requested {lr.type.lower()} ({days} day{'s' if days != 1 else ''}).",
            )
        )

    log_audit(
        db,
        actor_id=user.id,
        action="leave.request_created",
        entity_type="leave_request",
        entity_id=lr.id,
        payload={"type": lr.type, "start": str(s), "end": str(ed)},
        request=request,
    )
    db.commit()
    db.refresh(lr)
    summary = leave_detail_string(lr)
    background_tasks.add_task(notify_leave_new_request, requester_name=nm, summary=summary)
    return leave_to_frontend(lr)


@router.patch("/{leave_id}/status", response_model=dict)
def set_leave_status(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    leave_id: int,
    body: LeaveStatusUpdate,
    background_tasks: BackgroundTasks,
):
    lr = db.get(LeaveRequest, leave_id)
    if not lr:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Leave request not found")

    raw = body.status.strip().lower()
    if raw not in ("approved", "rejected"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Must be approved or rejected")
    status_new = LeaveStatus(raw)

    if lr.status != LeaveStatus.pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request already finalized")

    if not can_approve_leave(user, lr, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot approve this request")

    lr.status = status_new

    emp = db.get(Employee, lr.employee_id)
    if status_new == LeaveStatus.approved and emp:
        pol = resolve_policy_for_employee(db, emp)
        apply_leave_approval_ledger(
            db,
            employee_id=lr.employee_id,
            leave_type=lr.type,
            start=lr.start_date,
            end=lr.end_date,
            policy=pol,
        )

    log_audit(
        db,
        actor_id=user.id,
        action=f"leave.{status_new.value}",
        entity_type="leave_request",
        entity_id=lr.id,
        payload={"employee_id": lr.employee_id, "type": lr.type},
        request=request,
    )

    if emp:
        word = status_new.value
        db.add(
            Notification(
                target_id=emp.id,
                type="leave",
                dot="green" if status_new == LeaveStatus.approved else "red",
                title=f"{lr.type} {word.capitalize()}",
                text=f'Your leave request ({leave_detail_string(lr)}) was {word}.',
            )
        )

    db.commit()
    db.refresh(lr)

    if emp:
        nm = f'{emp.first} {emp.last}'.strip()
        background_tasks.add_task(
            notify_leave_decision,
            status_new.value,
            requester_name=nm,
            leave_summary=leave_detail_string(lr),
            requester_email=emp.email,
        )
    return leave_to_frontend(lr)
