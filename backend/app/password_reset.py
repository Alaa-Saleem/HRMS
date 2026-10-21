"""Opaque password reset / invite tokens (hashed at rest)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import Settings, public_ui_origin, settings
from app.mail_smtp import send_plain_email
from app.models import PasswordResetToken
from app.security import hash_refresh_token


def issue_password_token(db: Session, *, employee_id: int, purpose: str) -> str:
    plain = secrets.token_urlsafe(48)
    th = hash_refresh_token(plain)
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.password_reset_expire_hours)
    db.add(
        PasswordResetToken(
            employee_id=employee_id,
            token_hash=th,
            purpose=purpose,
            expires_at=exp,
        )
    )
    db.flush()
    return plain


def send_password_email(cfg: Settings, *, to_email: str, plain_token: str, purpose: str) -> None:
    base = public_ui_origin(cfg)
    link = f"{base}/reset-password.html?token={plain_token}"
    if purpose == "invite":
        subject = "Set your HRMS password"
        body = (
            "An administrator created or invited you to HRMS Suite.\n\n"
            f"Open this link to set your password (expires in {cfg.password_reset_expire_hours} hours):\n"
            f"{link}\n"
        )
    else:
        subject = "Reset your HRMS password"
        body = (
            "We received a request to reset your HRMS Suite password.\n\n"
            f"Open this link to choose a new password (expires in {cfg.password_reset_expire_hours} hours):\n"
            f"{link}\n\n"
            "If you did not request this, you can ignore this email.\n"
        )
    send_plain_email(cfg, to_addr=to_email, subject=subject, body=body)
