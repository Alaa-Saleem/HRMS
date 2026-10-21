"""Paginated audit trail for admins."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import CurrentUser, DbSession
from app.models import AuditEvent, Employee, Role

router = APIRouter(tags=["audit"])


def _parse_dt(raw: Optional[str]) -> Optional[datetime]:
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


@router.get("/audit-events", response_model=dict)
def list_audit_events(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action_prefix: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    actor_id: Optional[int] = Query(None),
    created_after: Optional[str] = Query(None),
    created_before: Optional[str] = Query(None),
):
    if user.role != Role.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")

    q = db.query(AuditEvent)
    if action_prefix:
        q = q.filter(AuditEvent.action.startswith(action_prefix.strip()))
    if entity_type:
        q = q.filter(AuditEvent.entity_type == entity_type.strip())
    if actor_id is not None:
        q = q.filter(AuditEvent.actor_employee_id == actor_id)

    ca = _parse_dt(created_after)
    if ca:
        q = q.filter(AuditEvent.created_at >= ca)
    cb = _parse_dt(created_before)
    if cb:
        q = q.filter(AuditEvent.created_at <= cb)

    total = q.count()
    rows = q.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit).all()

    actor_ids = {r.actor_employee_id for r in rows if r.actor_employee_id}
    emails: dict[int, str] = {}
    if actor_ids:
        for e in db.query(Employee.id, Employee.email).filter(Employee.id.in_(actor_ids)).all():
            emails[e.id] = e.email

    items: list[dict[str, Any]] = []
    for ev in rows:
        items.append(
            {
                "id": ev.id,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
                "actor_id": ev.actor_employee_id,
                "actor_email": emails.get(ev.actor_employee_id) if ev.actor_employee_id else None,
                "action": ev.action,
                "entity_type": ev.entity_type,
                "entity_id": ev.entity_id,
                "payload": ev.payload or {},
                "ip": ev.ip,
            }
        )
    return {"items": items, "total": total, "limit": limit, "offset": offset}
