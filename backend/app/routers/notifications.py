from fastapi import APIRouter
from starlette.responses import Response

from app.deps import CurrentUser, DbSession
from app.models import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/read-all")
def mark_all_read(db: DbSession, _user: CurrentUser):
    for n in db.query(Notification).all():
        n.read = True
    db.commit()
    return Response(status_code=204)
