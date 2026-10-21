"""Platform → Platform Users management.

Allows super_admin to manage the platform team (support agents, billing admins, etc.)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.deps import CurrentPlatformUser, DbSession
from app.models import AuditEvent, PlatformRole, PlatformUser
from app.security import hash_password

router = APIRouter(prefix="/platform/users", tags=["platform-users"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_super_admin(user):
    if user.platform_role != PlatformRole.super_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Super admin only")


def _user_row(pu: PlatformUser) -> dict:
    return {
        "id": pu.id,
        "email": pu.email,
        "full_name": pu.full_name,
        "platform_role": pu.platform_role.value,
        "is_active": pu.is_active,
        "last_login_at": pu.last_login_at.isoformat() if pu.last_login_at else None,
        "created_at": pu.created_at.isoformat() if pu.created_at else None,
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PlatformUserCreate(BaseModel):
    email: str
    password: str
    full_name: str = ""
    platform_role: PlatformRole = PlatformRole.support_agent


class PlatformUserUpdate(BaseModel):
    full_name: Optional[str] = None
    platform_role: Optional[PlatformRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=dict)
def list_platform_users(
    db: DbSession,
    user: CurrentPlatformUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    q = db.query(PlatformUser)
    total = q.count()
    users = (
        q.order_by(PlatformUser.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_user_row(u) for u in users],
    }


@router.get("/{user_id}", response_model=dict)
def get_platform_user(user_id: int, db: DbSession, user: CurrentPlatformUser):
    pu = db.get(PlatformUser, user_id)
    if not pu:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Platform user not found")
    return _user_row(pu)


@router.post("", response_model=dict, status_code=201)
def create_platform_user(db: DbSession, user: CurrentPlatformUser, body: PlatformUserCreate):
    _require_super_admin(user)

    email = body.email.strip().lower()
    existing = db.query(PlatformUser).filter(PlatformUser.email == email).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Email '{email}' already registered")

    pu = PlatformUser(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        platform_role=body.platform_role,
        is_active=True,
    )
    db.add(pu)
    db.flush()

    db.add(AuditEvent(
        actor_platform_user_id=user.id,
        action="platform.user.created",
        entity_type="platform_user",
        entity_id=pu.id,
        payload={"email": email, "role": body.platform_role.value},
    ))
    db.commit()
    return _user_row(pu)


@router.patch("/{user_id}", response_model=dict)
def update_platform_user(user_id: int, db: DbSession, user: CurrentPlatformUser, body: PlatformUserUpdate):
    _require_super_admin(user)
    pu = db.get(PlatformUser, user_id)
    if not pu:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Platform user not found")

    # Prevent demoting yourself accidentally
    if pu.id == user.id and body.platform_role is not None and body.platform_role != PlatformRole.super_admin:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot change your own role")
    if pu.id == user.id and body.is_active is False:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate yourself")

    if body.full_name is not None:     pu.full_name = body.full_name
    if body.platform_role is not None: pu.platform_role = body.platform_role
    if body.is_active is not None:     pu.is_active = body.is_active
    if body.password:                  pu.password_hash = hash_password(body.password)

    db.add(AuditEvent(
        actor_platform_user_id=user.id,
        action="platform.user.updated",
        entity_type="platform_user",
        entity_id=pu.id,
        payload={"role": body.platform_role.value if body.platform_role else None},
    ))
    db.commit()
    return _user_row(pu)


@router.delete("/{user_id}", response_model=dict)
def delete_platform_user(user_id: int, db: DbSession, user: CurrentPlatformUser):
    _require_super_admin(user)
    pu = db.get(PlatformUser, user_id)
    if not pu:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Platform user not found")
    if pu.id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete yourself")

    db.add(AuditEvent(
        actor_platform_user_id=user.id,
        action="platform.user.deleted",
        entity_type="platform_user",
        entity_id=pu.id,
        payload={"email": pu.email},
    ))
    db.delete(pu)
    db.commit()
    return {"ok": True, "deleted_user_id": user_id}
