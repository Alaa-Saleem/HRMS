"""Outbound email / Slack hooks (optional when env not configured)."""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def send_slack_message(text: str) -> bool:
    url = getattr(settings, "slack_webhook_url", None) or ""
    if not url.strip():
        return False
    try:
        r = httpx.post(url, json={"text": text[:4000]}, timeout=10.0)
        return r.status_code < 400
    except Exception as e:
        logger.warning("slack send failed: %s", e)
        return False


def send_email_stub(to_email: str, subject: str, body: str) -> bool:
    """SMTP send when configured; otherwise log-only stub."""
    host = getattr(settings, "smtp_host", None) or ""
    if not host.strip():
        logger.info("[email disabled] to=%s subject=%s", to_email, subject[:120])
        return False
    try:
        import smtplib
        from email.mime.text import MIMEText

        port = int(getattr(settings, "smtp_port", 587))
        user = getattr(settings, "smtp_user", "") or ""
        password = getattr(settings, "smtp_password", "") or ""
        mail_from = getattr(settings, "smtp_from", "") or user

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = mail_from
        msg["To"] = to_email

        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            if user:
                smtp.login(user, password)
            smtp.sendmail(mail_from, [to_email], msg.as_string())
        return True
    except Exception as e:
        logger.warning("smtp send failed: %s", e)
        return False


def notify_leave_new_request(*, requester_name: str, summary: str) -> None:
    text = f"[HRMS] New leave request: {requester_name} — {summary}"
    send_slack_message(text)


def notify_leave_decision(
    action: str, *, requester_name: str, leave_summary: str, requester_email: Optional[str]
) -> None:
    text = f"[HRMS] Leave {action}: {requester_name} — {leave_summary}"
    send_slack_message(text)
    if requester_email:
        send_email_stub(requester_email, f"Leave {action}", text)
