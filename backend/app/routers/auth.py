from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import update

from app.audit import log_audit
from app.config import settings
from app.deps import CurrentUser, DbSession
from app.mail_smtp import smtp_configured
from app.models import Employee, EmployeeCredential, PasswordResetToken, PlatformUser, RefreshToken
from app.login_rate import enforce_login_rate
from app.password_reset import issue_password_token, send_password_email
from app.schemas_http import ForgotPasswordRequest, LoginRequest, LogoutRequest, RefreshRequest, ResetPasswordRequest
from app.security import (
    create_access_token,
    hash_refresh_token,
    hash_password,
    new_refresh_token_plain_and_hash,
    verify_password,
)
from app.serialization import employee_to_frontend

router = APIRouter(tags=["auth"])

@router.post("/auth/login", response_model=dict)
def login(request: Request, db: DbSession, body: LoginRequest):
    ip = request.client.host if request.client else "unknown"
    enforce_login_rate(ip, max_requests=settings.login_rate_per_minute, window_seconds=60.0)
    email = body.email.strip().lower()
    emp = db.query(Employee).filter(Employee.email == email).first()
    if not emp and "@" not in email:
        emp = db.query(Employee).filter(Employee.email.like(f"{email}@%")).first()
    if not emp:
        # Check if this is a PlatformUser (Super Admin) trying to log in at the company portal
        pu = db.query(PlatformUser).filter(PlatformUser.email == email).first()
        if not pu and "@" not in email:
            pu = db.query(PlatformUser).filter(PlatformUser.email.like(f"{email}@%")).first()
        if pu:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "هذا الحساب خاص بإدارة المنصة (Super Admin) — يرجى تسجيل الدخول عبر بوابة السوبر أدمن: platform-admin.html",
            )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown email or password")
    cred = db.get(EmployeeCredential, emp.id)
    if not cred or not verify_password(body.password, cred.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown email or password")

    # Embed tenant_id in JWT for downstream data isolation
    token = create_access_token({"sub": emp.email, "tenant_id": emp.tenant_id})
    plain, thash = new_refresh_token_plain_and_hash()
    exp = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    db.add(RefreshToken(employee_id=emp.id, token_hash=thash, expires_at=exp))
    db.commit()

    dept = emp.department
    return {
        "access_token": token,
        "refresh_token": plain,
        "token_type": "bearer",
        "user": employee_to_frontend(emp, dept.name if dept else ""),
    }


@router.post("/auth/refresh", response_model=dict)
def refresh_session(db: DbSession, body: RefreshRequest):
    h = hash_refresh_token(body.refresh_token.strip())
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == h).first()
    now = datetime.now(timezone.utc)
    if not row or row.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    
    expires_at = row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
    if expires_at <= now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expired")

    emp = db.get(Employee, row.employee_id)
    if not emp:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    row.revoked_at = now
    plain, thash = new_refresh_token_plain_and_hash()
    exp = now + timedelta(days=settings.jwt_refresh_expire_days)
    db.add(RefreshToken(employee_id=emp.id, token_hash=thash, expires_at=exp))
    db.flush()

    email = emp.email.strip().lower()
    access = create_access_token({"sub": email, "tenant_id": emp.tenant_id})
    db.commit()

    dept = emp.department
    return {
        "access_token": access,
        "refresh_token": plain,
        "token_type": "bearer",
        "user": employee_to_frontend(emp, dept.name if dept else ""),
    }


@router.post("/auth/logout", response_model=dict)
def logout(db: DbSession, user: CurrentUser, body: LogoutRequest):
    now = datetime.now(timezone.utc)
    if body.refresh_token and body.refresh_token.strip():
        h = hash_refresh_token(body.refresh_token.strip())
        row = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == h,
                RefreshToken.employee_id == user.id,
            )
            .first()
        )
        if row:
            row.revoked_at = now
    else:
        db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.employee_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
    db.commit()
    return {"ok": True}


@router.get("/auth/me", response_model=dict)
def me(db: DbSession, user: CurrentUser):
    dept = user.department
    return employee_to_frontend(user, dept.name if dept else "")


@router.post("/auth/forgot-password", response_model=dict)
def forgot_password(db: DbSession, body: ForgotPasswordRequest):
    if not smtp_configured(settings):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Password reset email is not configured (set SMTP_HOST and related SMTP_* variables).",
        )
    email = body.email.strip().lower()
    emp = db.query(Employee).filter(Employee.email == email).first()
    if not emp:
        return {"ok": True, "message": "If that email exists, a reset link has been sent."}
    try:
        plain = issue_password_token(db, employee_id=emp.id, purpose="reset")
        send_password_email(settings, to_email=emp.email, plain_token=plain, purpose="reset")
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Could not send reset email. Try again later or contact support.",
        )
    return {"ok": True, "message": "If that email exists, a reset link has been sent."}


@router.post("/auth/reset-password", response_model=dict)
def reset_password(request: Request, db: DbSession, body: ResetPasswordRequest):
    if len(body.new_password) < settings.password_min_length:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Password must be at least {settings.password_min_length} characters.",
        )
    raw = body.token.strip()
    th = hash_refresh_token(raw)
    now = datetime.now(timezone.utc)
    row = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == th).first()
    if not row or row.used_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset link.")
        
    expires_at = row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
    if expires_at <= now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset link.")
    emp = db.get(Employee, row.employee_id)
    if not emp:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset link.")

    cred = db.get(EmployeeCredential, emp.id)
    if cred:
        cred.password_hash = hash_password(body.new_password)
    else:
        db.add(EmployeeCredential(employee_id=emp.id, password_hash=hash_password(body.new_password)))

    row.used_at = now
    db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.employee_id == emp.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    log_audit(
        db,
        actor_id=None,
        action="auth.password_reset_completed",
        entity_type="employee",
        entity_id=emp.id,
        payload={"purpose": row.purpose},
        request=request,
    )
    db.commit()
    return {"ok": True}
