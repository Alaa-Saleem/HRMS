"""Platform authentication — separate from company employee auth.

POST /platform/auth/login   → authenticates platform_users only
POST /platform/auth/refresh → refreshes a platform session
POST /platform/auth/logout  → revokes platform refresh token
GET  /platform/auth/me      → current platform user info
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.deps import CurrentPlatformUser, DbSession
from app.models import PlatformRefreshToken, PlatformUser
from app.security import (
    create_platform_token,
    hash_refresh_token,
    new_refresh_token_plain_and_hash,
    verify_password,
)
from app.config import settings

router = APIRouter(prefix="/platform/auth", tags=["platform-auth"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PlatformLoginRequest(BaseModel):
    email: str
    password: str


class PlatformRefreshRequest(BaseModel):
    refresh_token: str


class PlatformLogoutRequest(BaseModel):
    refresh_token: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _platform_user_info(pu: PlatformUser) -> dict:
    return {
        "id": pu.id,
        "email": pu.email,
        "full_name": pu.full_name,
        "platform_role": pu.platform_role.value if hasattr(pu.platform_role, "value") else str(pu.platform_role),
        "is_active": pu.is_active,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login", response_model=dict)
def platform_login(db: DbSession, body: PlatformLoginRequest):
    email = body.email.strip().lower()
    pu = db.query(PlatformUser).filter(PlatformUser.email == email).first()
    if not pu or not pu.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not verify_password(body.password, pu.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    # Update last login
    pu.last_login_at = datetime.now(timezone.utc)

    token = create_platform_token({"sub": pu.email, "platform_role": pu.platform_role.value})
    plain, thash = new_refresh_token_plain_and_hash()
    exp = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    db.add(PlatformRefreshToken(platform_user_id=pu.id, token_hash=thash, expires_at=exp))
    db.commit()

    return {
        "access_token": token,
        "refresh_token": plain,
        "token_type": "bearer",
        "user": _platform_user_info(pu),
    }


@router.post("/refresh", response_model=dict)
def platform_refresh(db: DbSession, body: PlatformRefreshRequest):
    h = hash_refresh_token(body.refresh_token.strip())
    row = db.query(PlatformRefreshToken).filter(PlatformRefreshToken.token_hash == h).first()
    now = datetime.now(timezone.utc)

    if not row or row.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    expires_at = row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
    if expires_at <= now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expired")

    pu = db.get(PlatformUser, row.platform_user_id)
    if not pu or not pu.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Platform user not found")

    row.revoked_at = now
    plain, thash = new_refresh_token_plain_and_hash()
    exp = now + timedelta(days=settings.jwt_refresh_expire_days)
    db.add(PlatformRefreshToken(platform_user_id=pu.id, token_hash=thash, expires_at=exp))
    db.flush()

    access = create_platform_token({"sub": pu.email, "platform_role": pu.platform_role.value})
    db.commit()

    return {
        "access_token": access,
        "refresh_token": plain,
        "token_type": "bearer",
        "user": _platform_user_info(pu),
    }


@router.post("/logout", response_model=dict)
def platform_logout(db: DbSession, user: CurrentPlatformUser, body: PlatformLogoutRequest):
    now = datetime.now(timezone.utc)
    if body.refresh_token and body.refresh_token.strip():
        h = hash_refresh_token(body.refresh_token.strip())
        row = db.query(PlatformRefreshToken).filter(
            PlatformRefreshToken.token_hash == h,
            PlatformRefreshToken.platform_user_id == user.id,
        ).first()
        if row:
            row.revoked_at = now
    db.commit()
    return {"ok": True}


@router.get("/me", response_model=dict)
def platform_me(user: CurrentPlatformUser):
    return _platform_user_info(user)
