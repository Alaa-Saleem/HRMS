from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DbSession
from app.models import ChatMessage, Notification
from app.schemas_http import ChatCreate
from app.serialization import chat_to_frontend, employee_to_frontend

router = APIRouter(prefix="/chat", tags=["chat"])


def _dept(db):
    from app.models import Department

    return {d.id: d.name for d in db.query(Department).all()}


@router.post("/messages", response_model=dict, status_code=status.HTTP_201_CREATED)
def post_message(db: DbSession, user: CurrentUser, body: ChatCreate):
    text = body.text.strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty message")

    cm = ChatMessage(sender_id=user.id, body=text)
    db.add(cm)
    db.flush()

    nm = employee_to_frontend(user, _dept(db).get(user.department_id, ""))
    who = (nm["first"] + " " + nm["last"]).strip()
    preview = text if len(text) <= 40 else text[:40] + "…"
    db.add(
        Notification(
            target_id=None,
            type="message",
            dot="blue",
            title="New Message",
            text=f'{who}: "{preview}"',
        )
    )

    db.commit()
    db.refresh(cm)
    return chat_to_frontend(cm)
