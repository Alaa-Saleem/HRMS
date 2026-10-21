"""Platform → Global Audit Log (all tenants in one view)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.deps import CurrentPlatformUser, DbSession
from app.models import AuditEvent, Employee, PlatformUser, Tenant

router = APIRouter(prefix="/platform/audit", tags=["platform-audit"])


@router.get("", response_model=dict)
def global_audit_log(
    db: DbSession,
    user: CurrentPlatformUser,
    tenant_id: Optional[int] = Query(None),
    action_like: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    q = db.query(AuditEvent)
    if tenant_id is not None:
        q = q.filter(AuditEvent.tenant_id == tenant_id)
    if action_like:
        q = q.filter(AuditEvent.action.ilike(f"%{action_like}%"))

    total = q.count()
    events = q.order_by(AuditEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Build actor name lookup (avoid N+1 via sets)
    emp_ids = {e.actor_employee_id for e in events if e.actor_employee_id}
    pu_ids  = {e.actor_platform_user_id for e in events if e.actor_platform_user_id}
    emps = {e.id: e for e in db.query(Employee).filter(Employee.id.in_(emp_ids)).all()} if emp_ids else {}
    pus  = {p.id: p for p in db.query(PlatformUser).filter(PlatformUser.id.in_(pu_ids)).all()} if pu_ids else {}

    # Tenant names
    tenant_ids = {e.tenant_id for e in events if e.tenant_id}
    tenants = {t.id: t.name for t in db.query(Tenant).filter(Tenant.id.in_(tenant_ids)).all()} if tenant_ids else {}

    def _actor_name(event: AuditEvent) -> str:
        if event.actor_platform_user_id and event.actor_platform_user_id in pus:
            pu = pus[event.actor_platform_user_id]
            return f"[Platform] {pu.full_name or pu.email}"
        if event.actor_employee_id and event.actor_employee_id in emps:
            e = emps[event.actor_employee_id]
            return f"{e.first} {e.last}"
        return "System"

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": ev.id,
                "action": ev.action,
                "entity_type": ev.entity_type,
                "entity_id": ev.entity_id,
                "tenant_id": ev.tenant_id,
                "tenant_name": tenants.get(ev.tenant_id, "—") if ev.tenant_id else "Platform",
                "actor": _actor_name(ev),
                "ip": ev.ip,
                "payload": ev.payload,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            }
            for ev in events
        ],
    }
