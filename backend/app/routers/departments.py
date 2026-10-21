from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.deps import CurrentUser, DbSession
from app.models import Department, DepartmentFeatureFlag, Employee
from app.rbac import department_admin
from app.schemas_http import DepartmentCreate, DepartmentUpdate


class DepartmentFlagBody(BaseModel):
    value: Optional[Any] = None

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("")
def list_departments(db: DbSession, user: CurrentUser):
    rows = db.query(Department).order_by(Department.name.asc()).all()
    return [
        {"id": d.id, "name": d.name, "code": d.code, "is_active": d.is_active}
        for d in rows
    ]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict)
def create_department(db: DbSession, user: CurrentUser, body: DepartmentCreate):
    if not department_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    name = body.name.strip()
    if db.query(Department).filter(Department.name == name).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Department exists")
    d = Department(name=name, code=body.code.strip() if body.code else None, is_active=True)
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"id": d.id, "name": d.name, "code": d.code, "is_active": d.is_active}


@router.patch("/{dept_id}", response_model=dict)
def update_department(db: DbSession, user: CurrentUser, dept_id: int, body: DepartmentUpdate):
    if not department_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    d = db.get(Department, dept_id)
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    if body.name is not None:
        clash = db.query(Department).filter(Department.name == body.name.strip(), Department.id != dept_id).first()
        if clash:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Name taken")
        d.name = body.name.strip()
    if body.code is not None:
        d.code = body.code.strip() or None
    if body.is_active is not None:
        d.is_active = body.is_active
    db.commit()
    db.refresh(d)
    return {"id": d.id, "name": d.name, "code": d.code, "is_active": d.is_active}


@router.get("/{dept_id}/flags", response_model=dict)
def get_department_flags(db: DbSession, user: CurrentUser, dept_id: int):
    if not db.get(Department, dept_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    rows = db.query(DepartmentFeatureFlag).filter(DepartmentFeatureFlag.department_id == dept_id).all()
    return {r.flag_key: r.flag_value for r in rows}


@router.put("/{dept_id}/flags/{flag_key}", response_model=dict)
def put_department_flag(
    db: DbSession,
    user: CurrentUser,
    dept_id: int,
    flag_key: str,
    body: DepartmentFlagBody,
):
    if not department_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    if not db.get(Department, dept_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    key = flag_key.strip()[:64]
    if not key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid flag key")
    row = (
        db.query(DepartmentFeatureFlag)
        .filter(
            DepartmentFeatureFlag.department_id == dept_id,
            DepartmentFeatureFlag.flag_key == key,
        )
        .first()
    )
    val = body.value
    stored = val if isinstance(val, dict) else {"v": val}
    if row:
        row.flag_value = stored
    else:
        row = DepartmentFeatureFlag(department_id=dept_id, flag_key=key, flag_value=stored)
        db.add(row)
    db.commit()
    db.refresh(row)
    return {"department_id": dept_id, "flag_key": key, "flag_value": row.flag_value}


@router.delete("/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
def soft_delete_department(db: DbSession, user: CurrentUser, dept_id: int):
    if not department_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    d = db.get(Department, dept_id)
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    if db.query(Employee).filter(Employee.department_id == dept_id).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Department still has employees — reassign first")
    d.is_active = False
    db.commit()
    return None
