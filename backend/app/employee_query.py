"""Shared employee listing queries (visibility + filters)."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.models import Employee
from app.rbac import list_visible_employee_ids


def apply_visibility_to_query(db: Session, user: Employee, query: Query) -> Query:
    visible = list_visible_employee_ids(db, user)
    if visible is not None:
        ids = list(visible)
        if not ids:
            return query.filter(Employee.id == -1)
        return query.filter(Employee.id.in_(ids))
    return query


def apply_search_filters_query(
    query: Query,
    *,
    q: str | None,
    department_id: int | None,
    status: str | None,
) -> Query:
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Employee.first.ilike(term),
                Employee.last.ilike(term),
                Employee.email.ilike(term),
                Employee.title.ilike(term),
            )
        )
    if department_id is not None:
        query = query.filter(Employee.department_id == department_id)
    if status and status.strip():
        query = query.filter(Employee.status == status.strip().lower())
    return query
