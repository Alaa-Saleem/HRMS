"""Minimal SMTP sender for password reset / invite (no secrets logged)."""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from app.config import Settings

logger = logging.getLogger(__name__)


def smtp_configured(settings: Settings) -> bool:
    return bool(settings.smtp_host and settings.smtp_host.strip())


def send_plain_email(settings: Settings, *, to_addr: str, subject: str, body: str) -> None:
    if not smtp_configured(settings):
        raise RuntimeError("SMTP is not configured")
    mail_from = (settings.smtp_from or settings.smtp_user or "").strip()
    if not mail_from:
        raise RuntimeError("SMTP_FROM or SMTP_USER must be set")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = to_addr

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.sendmail(mail_from, [to_addr], msg.as_string())
    except OSError as e:
        logger.warning("smtp send failed: %s", type(e).__name__)
        raise
