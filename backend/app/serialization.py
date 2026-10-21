"""Map ORM rows to frontend-friendly JSON (camelCase, nested attendance/leave)."""
from __future__ import annotations

from datetime import date

from app.models import (
    ChatMessage,
    Employee,
    LeaveRequest,
    Notification,
    Task,
)


def _iso_date(d: date | None) -> str | None:
    if d is None:
        return None
    return d.isoformat()


def employee_to_frontend(e: Employee, department_name: str) -> dict:
    lb = e.leave_balance if isinstance(e.leave_balance, dict) else {}
    att = e.attendance if isinstance(e.attendance, dict) else {}
    return {
        "id": e.id,
        "first": e.first,
        "last": e.last,
        "initials": e.initials,
        "email": e.email,
        "phone": e.phone,
        "role": e.role.value if hasattr(e.role, "value") else str(e.role),
        "department": department_name,
        "department_id": e.department_id,
        "title": e.title,
        "salary": e.salary,
        "status": e.status,
        "start": _iso_date(e.start),
        "managerId": e.manager_id,
        "dob": _iso_date(e.dob),
        "gender": e.gender,
        "nationality": e.nationality,
        "marital": e.marital,
        "address": e.address,
        "emergency": e.emergency,
        "rating": e.rating,
        "goalsCompleted": e.goals_completed,
        "peerReviews": e.peer_reviews,
        "attendance": {
            "present": att.get("present", 0),
            "late": att.get("late", 0),
            "absent": att.get("absent", 0),
            "avgHrs": str(att.get("avgHrs", "0")),
        },
        "leave": {
            "annual": lb.get("annual", "0 / 0"),
            "sick": lb.get("sick", "0 / 0"),
            "personal": lb.get("personal", "0 / 0"),
        },
    }


def leave_to_frontend(lr: LeaveRequest) -> dict:
    return {
        "id": lr.id,
        "empId": lr.employee_id,
        "type": lr.type,
        "start": _iso_date(lr.start_date),
        "end": _iso_date(lr.end_date),
        "reason": lr.reason or "",
        "status": lr.status.value if hasattr(lr.status, "value") else str(lr.status),
    }


def pending_approval_row(lr: LeaveRequest, detail: str) -> dict:
    """Legacy-compatible row for dashboards that keyed off empId + detail."""
    return {
        "leaveId": lr.id,
        "empId": lr.employee_id,
        "type": lr.type,
        "detail": detail,
        "status": lr.status.value if hasattr(lr.status, "value") else str(lr.status),
    }


def leave_detail_string(lr: LeaveRequest) -> str:
    s = lr.start_date.strftime("%b %d")
    ed = lr.end_date.strftime("%b %d")
    days = (lr.end_date - lr.start_date).days + 1
    suf = "day" if days == 1 else "days"
    extra = (" — " + lr.reason.strip()) if lr.reason and lr.reason.strip() else ""
    return f"{s} – {ed} ({days} {suf}){extra}"


def task_to_frontend(t: Task, index: int) -> dict:
    return {
        "id": t.id,
        "_idx": index,
        "title": t.title,
        "assigneeId": t.assignee_id,
        "due": t.due,
        "status": t.status.value if hasattr(t.status, "value") else str(t.status),
        "priority": t.priority,
    }


def notification_to_frontend(n: Notification) -> dict:
    tm = ""
    if n.created_at:
        tm = n.created_at.strftime("%I:%M %p").replace(" 0", " ").strip()
    return {
        "id": n.id,
        "targetId": n.target_id,
        "type": n.type,
        "dot": n.dot,
        "title": n.title,
        "text": n.text,
        "time": tm,
        "read": n.read,
    }


def chat_to_frontend(cm: ChatMessage) -> dict:
    t = ""
    if cm.created_at:
        raw = cm.created_at.strftime("%I:%M %p")
        if raw.startswith("0"):
            raw = raw[1:]
        t = raw
    return {
        "id": cm.id,
        "senderId": cm.sender_id,
        "text": cm.body,
        "time": t,
    }
