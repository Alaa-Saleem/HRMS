from __future__ import annotations

import csv
import io
import json
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import text

from app.audit import log_audit
from app.config import settings
from app.deps import CurrentUser, DbSession
from app.mail_smtp import smtp_configured
from app.password_reset import issue_password_token, send_password_email
from app.employee_query import apply_search_filters_query, apply_visibility_to_query
from app.models import Department, Employee, EmployeeCredential, Notification, RefreshToken, Role, Task
from app.rbac import (
    can_delete_employee,
    can_modify_employee,
    department_admin,
    list_visible_employee_ids,
)
from app.schemas_http import EmployeeCreate, EmployeeImportResult, EmployeeUpdate
from app.security import hash_password
from app.serialization import employee_to_frontend

router = APIRouter(prefix="/employees", tags=["employees"])


def _department_map(db):
    return {d.id: d.name for d in db.query(Department).all()}


def _parse_role(role_s: str) -> Role:
    try:
        return Role(role_s)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid role") from None


def _parse_csv_date(value: Optional[str]) -> date:
    if not value or not str(value).strip():
        return date.today()
    s = str(value).strip()[:10]
    return date.fromisoformat(s)


def _can_view_employee_profile(actor: Employee, target_id: int, db) -> bool:
    if actor.role == Role.admin:
        return True
    if actor.id == target_id:
        return True
    vis = list_visible_employee_ids(db, actor)
    if vis is None:
        return True
    return target_id in vis


@router.get("", response_model=dict)
def list_employees(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    base = db.query(Employee)
    base = apply_visibility_to_query(db, user, base)
    base = apply_search_filters_query(base, q=q, department_id=department_id, status=status_filter)
    total = base.count()
    rows = base.order_by(Employee.last.asc(), Employee.first.asc()).offset(offset).limit(limit).all()
    dm = _department_map(db)
    items = [employee_to_frontend(e, dm.get(e.department_id, "")) for e in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/export")
def export_employees(
    db: DbSession,
    user: CurrentUser,
    export_format: str = Query("csv", alias="format"),
):
    export_format = (export_format or "csv").lower()
    if export_format not in ("csv", "json"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "format must be csv or json")
    base = db.query(Employee)
    base = apply_visibility_to_query(db, user, base)
    rows = base.order_by(Employee.id.asc()).all()
    dm = _department_map(db)
    items = [employee_to_frontend(e, dm.get(e.department_id, "")) for e in rows]
    if export_format == "json":
        return Response(
            content=json.dumps({"employees": items}, default=str),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="employees.json"'},
        )
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "id",
            "first",
            "last",
            "email",
            "phone",
            "role",
            "department_id",
            "department",
            "title",
            "salary",
            "status",
            "start",
            "manager_id",
        ]
    )
    for it in items:
        w.writerow(
            [
                it["id"],
                it["first"],
                it["last"],
                it["email"],
                it["phone"],
                it["role"],
                it["department_id"],
                it["department"],
                it["title"],
                it["salary"],
                it["status"],
                it["start"],
                it.get("managerId"),
            ]
        )
    data = buf.getvalue()
    return Response(
        content=data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="employees_export.csv"'},
    )


@router.post("/import", response_model=EmployeeImportResult)
async def import_employees(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    dry_run: bool = Query(False),
    upsert: bool = Query(False),
    file: Optional[UploadFile] = File(None),
):
    if not department_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    result = EmployeeImportResult()
    rows_data: List[Dict[str, Any]] = []

    ct = (request.headers.get("content-type") or "").lower()
    if "application/json" in ct:
        body = await request.json()
        if isinstance(body, list):
            rows_data = body
        elif isinstance(body, dict) and "employees" in body:
            rows_data = body["employees"]
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "JSON must be a list or {employees: [...]}")
    elif file and file.filename:
        raw = (await file.read()).decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(raw))
        for row in reader:
            rows_data.append(dict(row))
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Send CSV file as multipart 'file' or JSON array body")

    for i, raw in enumerate(rows_data):
        row_num = i + 1
        try:
            email = str(raw.get("email", "")).strip().lower()
            if not email:
                result.errors.append({"row": row_num, "error": "missing email"})
                result.skipped += 1
                continue
            first = str(raw.get("first", "")).strip()
            last = str(raw.get("last", "")).strip()
            if not first or not last:
                result.errors.append({"row": row_num, "error": "first and last required"})
                result.skipped += 1
                continue
            dept_id = int(float(raw.get("department_id") or 0))
            if not dept_id:
                result.errors.append({"row": row_num, "error": "department_id required"})
                result.skipped += 1
                continue
            if not db.get(Department, dept_id):
                result.errors.append({"row": row_num, "error": f"invalid department_id {dept_id}"})
                result.skipped += 1
                continue
            role = _parse_role(str(raw.get("role", "employee")).strip().lower())
            salary = float(raw.get("salary") or 0)
            title = str(raw.get("title", "")).strip()
            phone = str(raw.get("phone", "")).strip()
            mgr_raw = raw.get("manager_id")
            manager_id = int(mgr_raw) if mgr_raw not in (None, "", "null") else None
            start = _parse_csv_date(raw.get("start"))
            existing = db.query(Employee).filter(Employee.email == email).first()
            if existing:
                if not upsert:
                    result.skipped += 1
                    continue
                if dry_run:
                    result.updated += 1
                    continue
                existing.first = first
                existing.last = last
                existing.initials = (first[:1] + last[:1]).upper()
                existing.phone = phone
                existing.role = role
                existing.title = title
                existing.salary = salary
                existing.start = start
                existing.department_id = dept_id
                existing.manager_id = manager_id
                result.updated += 1
            else:
                if dry_run:
                    result.created += 1
                    continue
                pwd_plain = str(raw.get("password", "")).strip() or f"{first.lower()}@123"
                initials = (first[:1] + last[:1]).upper()
                emp = Employee(
                    first=first,
                    last=last,
                    initials=initials,
                    email=email,
                    phone=phone,
                    role=role,
                    title=title or "New Hire",
                    salary=salary,
                    status="active",
                    start=start,
                    manager_id=manager_id,
                    department_id=dept_id,
                    dob=None,
                    gender="Other",
                    nationality="United States",
                    marital="Single",
                    address="Remote",
                    emergency="—",
                    rating=0,
                    goals_completed="0 / 10",
                    peer_reviews=0,
                    attendance={"present": 0, "late": 0, "absent": 0, "avgHrs": "0"},
                    leave_balance={"annual": "20 / 20", "sick": "10 / 10", "personal": "5 / 5"},
                )
                db.add(emp)
                db.flush()
                db.add(
                    EmployeeCredential(
                        employee_id=emp.id,
                        password_hash=hash_password(pwd_plain),
                    )
                )
                result.created += 1
        except Exception as ex:
            result.errors.append({"row": row_num, "error": str(ex)})
            result.skipped += 1

    if not dry_run and (result.created or result.updated):
        log_audit(
            db,
            actor_id=user.id,
            action="employee.bulk_import",
            entity_type="employee",
            entity_id=None,
            payload={"created": result.created, "updated": result.updated, "dry_run": False},
            request=request,
        )
        db.commit()
    elif dry_run:
        db.rollback()
    return result


@router.get("/{employee_id}/reporting-tree", response_model=dict)
def reporting_tree(db: DbSession, user: CurrentUser, employee_id: int):
    if not _can_view_employee_profile(user, employee_id, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot view this org subtree")
    sql = text(
        """
        WITH RECURSIVE subtree AS (
          SELECT id, manager_id, first, last, department_id, role::text AS role, 1 AS depth
          FROM employees WHERE manager_id = :root
          UNION ALL
          SELECT e.id, e.manager_id, e.first, e.last, e.department_id, e.role::text, subtree.depth + 1
          FROM employees e
          INNER JOIN subtree ON e.manager_id = subtree.id
        )
        SELECT id, manager_id, first, last, department_id, role, depth FROM subtree
        ORDER BY depth, id
        """
    )
    dm = _department_map(db)
    rows = db.execute(sql, {"root": employee_id}).mappings().all()
    nodes = []
    for r in rows:
        dept_name = dm.get(r["department_id"], "")
        nodes.append(
            {
                "id": r["id"],
                "managerId": r["manager_id"],
                "name": f'{r["first"]} {r["last"]}'.strip(),
                "department": dept_name,
                "role": r["role"],
                "depth": r["depth"],
            }
        )
    return {"rootEmployeeId": employee_id, "descendants": nodes}


@router.post("/{employee_id}/invite-password-reset", response_model=dict)
def invite_password_reset(request: Request, db: DbSession, user: CurrentUser, employee_id: int):
    if not department_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    if not smtp_configured(settings):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Invite email is not configured (set SMTP_HOST and related SMTP_* variables).",
        )
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    try:
        plain = issue_password_token(db, employee_id=emp.id, purpose="invite")
        send_password_email(settings, to_email=emp.email, plain_token=plain, purpose="invite")
        log_audit(
            db,
            actor_id=user.id,
            action="employee.invite_password_reset",
            entity_type="employee",
            entity_id=emp.id,
            payload={},
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Could not send invite email. Try again later.",
        )
    return {"ok": True}


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_employee(request: Request, db: DbSession, user: CurrentUser, body: EmployeeCreate):
    if not department_admin(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only admins create employees")

    dept = db.get(Department, body.department_id)
    if not dept:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid department")

    email = body.email.strip().lower()
    if db.query(Employee).filter(Employee.email == email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email taken")

    role = _parse_role(body.role)
    initials = ((body.first[:1] + body.last[:1]) if body.first and body.last else "??").upper()
    pwd_plain = body.password.strip() or f"{(body.first or 'user').lower()}@123"

    emp = Employee(
        first=body.first.strip(),
        last=body.last.strip(),
        initials=initials,
        email=email,
        phone=(body.phone or "").strip(),
        role=role,
        title=(body.title or "").strip(),
        salary=body.salary,
        status="active",
        start=body.start,
        manager_id=body.manager_id,
        department_id=body.department_id,
        dob=None,
        gender="Other",
        nationality="United States",
        marital="Single",
        address="Remote",
        emergency="—",
        rating=0,
        goals_completed="0 / 10",
        peer_reviews=0,
        attendance={"present": 0, "late": 0, "absent": 0, "avgHrs": "0"},
        leave_balance={"annual": "20 / 20", "sick": "10 / 10", "personal": "5 / 5"},
    )
    db.add(emp)
    db.flush()

    db.add(
        EmployeeCredential(
            employee_id=emp.id,
            password_hash=hash_password(pwd_plain),
        )
    )
    db.add(
        Notification(
            target_id=None,
            type="employee",
            dot="blue",
            title="New Employee Added",
            text=f"{emp.first} {emp.last} joined as {role.value} in {dept.name}.",
        )
    )
    log_audit(
        db,
        actor_id=user.id,
        action="employee.created",
        entity_type="employee",
        entity_id=emp.id,
        payload={"email": emp.email, "role": role.value},
        request=request,
    )
    db.commit()
    db.refresh(emp)

    dm = _department_map(db)
    return employee_to_frontend(emp, dm.get(emp.department_id, ""))


@router.patch("/{employee_id}", response_model=dict)
def update_employee(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    employee_id: int,
    body: EmployeeUpdate,
):
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    if not can_modify_employee(user, emp, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot edit this employee")

    old_salary = emp.salary
    old_status = emp.status

    if body.email and body.email.strip().lower() != emp.email:
        taken = db.query(Employee).filter(Employee.email == body.email.strip().lower()).first()
        if taken and taken.id != emp.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email taken")

    if body.first is not None:
        emp.first = body.first.strip()
    if body.last is not None:
        emp.last = body.last.strip()
    if body.first is not None or body.last is not None:
        emp.initials = (emp.first[:1] + emp.last[:1]).upper()

    if body.email:
        emp.email = body.email.strip().lower()
    if body.phone is not None:
        emp.phone = body.phone.strip()
    if body.role:
        emp.role = _parse_role(body.role)
    if body.department_id is not None:
        if not db.get(Department, body.department_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid department")
        emp.department_id = body.department_id
    if body.title is not None:
        emp.title = body.title.strip()
    if body.salary is not None:
        emp.salary = body.salary
    if body.start is not None:
        emp.start = body.start
    if body.manager_id is not None:
        emp.manager_id = body.manager_id
    if body.status is not None:
        emp.status = body.status
    if body.address is not None:
        emp.address = body.address.strip()
    if body.emergency is not None:
        emp.emergency = body.emergency.strip()

    if body.password and body.password.strip():
        cred = db.get(EmployeeCredential, emp.id)
        if not cred:
            cred = EmployeeCredential(employee_id=emp.id, password_hash="")
            db.add(cred)
        cred.password_hash = hash_password(body.password.strip())
        db.query(RefreshToken).filter(RefreshToken.employee_id == emp.id).delete()
        log_audit(
            db,
            actor_id=user.id,
            action="employee.password_changed",
            entity_type="employee",
            entity_id=emp.id,
            payload={"changed": True},
            request=request,
        )

    if body.salary is not None and emp.salary != old_salary:
        log_audit(
            db,
            actor_id=user.id,
            action="employee.salary_changed",
            entity_type="employee",
            entity_id=emp.id,
            payload={"from": old_salary, "to": emp.salary},
            request=request,
        )

    if body.status is not None and emp.status != old_status:
        log_audit(
            db,
            actor_id=user.id,
            action="employee.status_changed",
            entity_type="employee",
            entity_id=emp.id,
            payload={"from": old_status, "to": emp.status},
            request=request,
        )

    db.commit()
    db.refresh(emp)
    dm = _department_map(db)
    return employee_to_frontend(emp, dm.get(emp.department_id, ""))


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(request: Request, db: DbSession, user: CurrentUser, employee_id: int):
    if not can_delete_employee(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")

    if employee_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete yourself")

    if db.query(Task).filter(Task.assignee_id == employee_id).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Reassign tasks before deleting employee")

    if db.query(Employee).filter(Employee.manager_id == employee_id).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Reassign reporting lines before deleting")

    log_audit(
        db,
        actor_id=user.id,
        action="employee.deleted",
        entity_type="employee",
        entity_id=employee_id,
        payload={"email": emp.email},
        request=request,
    )
    db.delete(emp)
    db.commit()
    return None
