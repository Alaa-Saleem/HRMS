from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import AuditEvent


def client_ip_from_request(request: Any) -> Optional[str]:
    if request is None:
        return None
    try:
        if request.client:
            return request.client.host
    except Exception:
        pass
    return None


def log_audit(
    db: Session,
    *,
    actor_id: Optional[int],
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    payload: Optional[dict[str, Any]] = None,
    request: Any = None,
) -> None:
    ip = client_ip_from_request(request)
    db.add(
        AuditEvent(
            actor_employee_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
            ip=ip,
        )
    )
