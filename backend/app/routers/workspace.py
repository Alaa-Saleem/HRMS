from fastapi import APIRouter

from app.deps import CurrentUser, DbSession
from app.models import (
    ChatMessage,
    Department,
    Employee,
    LeaveRequest,
    LeaveStatus,
    Notification,
    Role,
    Task,
)
from app.rbac import list_visible_employee_ids
from app.serialization import (
    chat_to_frontend,
    employee_to_frontend,
    leave_to_frontend,
    leave_detail_string,
    notification_to_frontend,
    pending_approval_row,
    task_to_frontend,
)

router = APIRouter(tags=["workspace"])


@router.get("/workspace", response_model=dict)
def get_workspace(db: DbSession, user: CurrentUser):
    visible = list_visible_employee_ids(db, user)

    dept_map = {d.id: d.name for d in db.query(Department).all()}

    q = db.query(Employee)
    if visible is not None:
        q = q.filter(Employee.id.in_(visible))
    employees = q.all()
    emp_json = [employee_to_frontend(e, dept_map.get(e.department_id, "")) for e in employees]

    departments = [
        {"id": d.id, "name": d.name, "code": d.code, "is_active": d.is_active}
        for d in db.query(Department).filter(Department.is_active.is_(True)).order_by(Department.name.asc()).all()
    ]

    leaves_all = db.query(LeaveRequest).order_by(LeaveRequest.id.asc()).all()

    if user.role == Role.employee:
        leaves_db = [lr for lr in leaves_all if lr.employee_id == user.id]
        pending_filtered: list[LeaveRequest] = []
    elif user.role == Role.manager:
        leaves_db = leaves_all
        pending_filtered = []
        for lr in leaves_all:
            if lr.status != LeaveStatus.pending:
                continue
            rq = db.get(Employee, lr.employee_id)
            if rq and rq.manager_id == user.id:
                pending_filtered.append(lr)
    else:
        leaves_db = leaves_all
        pending_filtered = [lr for lr in leaves_all if lr.status == LeaveStatus.pending]

    leave_json = [leave_to_frontend(lr) for lr in leaves_db]
    approvals = [pending_approval_row(lr, leave_detail_string(lr)) for lr in pending_filtered]

    tasks_db = db.query(Task).order_by(Task.id.asc()).all()
    task_json = [task_to_frontend(t, i) for i, t in enumerate(tasks_db)]

    notifications_db = db.query(Notification).order_by(Notification.id.desc()).all()

    def notif_visible(n: Notification) -> bool:
        if n.target_id is None:
            return True
        if n.target_id == user.id:
            return True
        if user.role == Role.admin:
            return True
        if user.role == Role.manager:
            targ = db.get(Employee, n.target_id)
            return bool(targ and targ.manager_id == user.id)
        return False

    notification_json = [notification_to_frontend(n) for n in notifications_db if notif_visible(n)]

    chat_db = db.query(ChatMessage).order_by(ChatMessage.id.asc()).all()
    chat_json = [chat_to_frontend(c) for c in chat_db]

    me_full = employee_to_frontend(user, dept_map.get(user.department_id, ""))

    return {
        "user": me_full,
        "employees": emp_json,
        "departments": departments,
        "leaveRequests": leave_json,
        "pendingApprovals": approvals,
        "tasks": task_json,
        "notifications": notification_json,
        "chatMessages": chat_json,
    }
