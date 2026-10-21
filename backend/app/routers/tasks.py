from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DbSession
from app.models import Employee, Notification, Task, TaskStatus
from app.rbac import can_assign_task, can_move_task
from app.schemas_http import TaskCreate, TaskMove
from app.serialization import employee_to_frontend, task_to_frontend

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _dept(db):
    from app.models import Department

    return {d.id: d.name for d in db.query(Department).all()}


def _all_tasks_ordered(db):
    return db.query(Task).order_by(Task.id.asc()).all()


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_task(db: DbSession, user: CurrentUser, body: TaskCreate):
    if not can_assign_task(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only managers and admins assign tasks")

    assignee = db.get(Employee, body.assignee_id)
    if not assignee:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid assignee")

    try:
        st = TaskStatus(body.status.strip().lower())
    except ValueError:
        st = TaskStatus.todo

    t = Task(
        title=body.title.strip(),
        assignee_id=body.assignee_id,
        due=body.due,
        status=st,
        priority=body.priority,
    )
    db.add(t)
    db.flush()

    nm = employee_to_frontend(user, _dept(db).get(user.department_id, ""))
    who = (nm["first"] + " " + nm["last"]).strip()
    due_part = f" Due {t.due}." if t.due else ""
    db.add(
        Notification(
            target_id=assignee.id,
            type="task",
            dot="blue",
            title="New Task Assigned",
            text=f'"{t.title}" assigned to you by {who}.{due_part}',
        )
    )

    db.commit()
    db.refresh(t)
    all_tasks = _all_tasks_ordered(db)
    idx = next((i for i, tt in enumerate(all_tasks) if tt.id == t.id), 0)
    return task_to_frontend(t, idx)


@router.patch("/{task_id}/move", response_model=dict)
def move_task(db: DbSession, user: CurrentUser, task_id: int, body: TaskMove):
    t = db.get(Task, task_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    if not can_move_task(user, t, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot move this task")

    try:
        st = TaskStatus(body.status.strip().lower())
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status") from None

    t.status = st
    if st == TaskStatus.done:
        t.due = None
        t.priority = None

    db.commit()
    db.refresh(t)
    all_tasks = _all_tasks_ordered(db)
    idx = next((i for i, tt in enumerate(all_tasks) if tt.id == t.id), 0)
    return task_to_frontend(t, idx)
