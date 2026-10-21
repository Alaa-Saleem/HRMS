"""Role-based access helpers (mirrors frontend rules in shell + bootstrap).

NOTE: super_admin no longer exists as a company role — it is a PlatformUser role.
The highest role within a company is now 'admin'.
"""
from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Employee, LeaveRequest, Role, Task


def list_visible_employee_ids(db: Session, user: Employee) -> set[int] | None:
    """None means all employees visible (admin sees all within tenant)."""
    if user.role == Role.admin:
        return None

    if user.role == Role.manager:
        ids = (
            db.query(Employee.id)
            .filter(or_(Employee.manager_id == user.id, Employee.id == user.id))
            .all()
        )
        return {r[0] for r in ids}

    # employee: self only for directory views
    return {user.id}


def can_manage_documents(actor: Employee, target: Employee, db: Session) -> bool:
    if actor.role == Role.admin:
        return True
    if actor.role == Role.manager:
        return target.manager_id == actor.id or target.id == actor.id
    return actor.id == target.id


def can_modify_employee(actor: Employee, target: Employee, db: Session) -> bool:
    if actor.role == Role.admin:
        return True
    if actor.role == Role.manager:
        return target.manager_id == actor.id or target.id == actor.id
    return actor.id == target.id


def can_create_employee(actor: Employee) -> bool:
    return actor.role == Role.admin


def can_delete_employee(actor: Employee) -> bool:
    return actor.role == Role.admin


def can_approve_leave(actor: Employee, leave: LeaveRequest, db: Session) -> bool:
    if actor.role == Role.admin:
        return True
    if actor.role != Role.manager:
        return False
    requester = db.get(Employee, leave.employee_id)
    if not requester:
        return False
    return requester.manager_id == actor.id


def can_assign_task(actor: Employee) -> bool:
    return actor.role in (Role.admin, Role.manager)


def can_move_task(actor: Employee, task: Task, db: Session) -> bool:
    if actor.role == Role.admin:
        return True
    if actor.role != Role.manager:
        return False
    assignee = db.get(Employee, task.assignee_id)
    if assignee:
        return assignee.manager_id == actor.id or assignee.id == actor.id
    return False


def department_admin(actor: Employee) -> bool:
    return actor.role == Role.admin
