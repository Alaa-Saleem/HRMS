#!/usr/bin/env python3
"""Add the 5 new departments + 20 demo people without removing existing data.

Idempotent: skips any row whose email already exists. Safe to re-run.

  cd backend && DATABASE_URL=... python scripts/seed_expansion.py

Requires an admin (any `Role.admin`) and — for Eng/Product ICs — employees with
`rita.gomez@company.com` and `tanya.johnson@company.com` as in the main seed.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models import Department, Employee, EmployeeCredential, Role  # noqa: E402
from app.security import hash_password  # noqa: E402


def pw(first: str, last: str) -> str:
    return f"{first.lower()}.{last.lower()}@123"


NEW_DEPARTMENTS: list[tuple[str, str]] = [
    ("Legal", "LGL"),
    ("Sales", "SLS"),
    ("Research", "RND"),
    ("Operations", "OPS"),
    ("Design", "DSN"),
]


@dataclass
class Row:
    first: str
    last: str
    email: str
    phone: str
    role: Role
    title: str
    salary: float
    started: date
    dept_name: str
    password: str
    manager_key: str  # "admin" | "rita" | "tanya" | mgr ref below
    dob: Optional[date] = None
    goals_completed: str = "4 / 10"
    peer_reviews: int = 2
    rating: float = 4.0
    attendance: Optional[dict[str, Any]] = None


# manager_key must match attribute names on expansion result object
MANAGERS: list[Row] = [
    Row("Marcus", "Hale", "marcus.hale@company.com", "+1 (555) 401-1101", Role.manager, "Finance Manager", 142000, date(2019, 5, 13), "Finance", pw("Marcus", "Hale"), "admin", dob=date(1985, 4, 22), attendance={"present": 236, "late": 2, "absent": 0, "avgHrs": "8.4"}),
    Row("Elena", "Park", "elena.park@company.com", "+1 (555) 401-1102", Role.manager, "HR Manager", 138000, date(2019, 8, 19), "Human Resources", pw("Elena", "Park"), "admin", dob=date(1988, 11, 8), peer_reviews=5, attendance={"present": 228, "late": 3, "absent": 1, "avgHrs": "8.3"}),
    Row("Omar", "Farouk", "omar.farouk@company.com", "+1 (555) 401-1103", Role.manager, "Support Manager", 125000, date(2020, 1, 6), "Support", pw("Omar", "Farouk"), "admin", dob=date(1990, 3, 14), attendance={"present": 220, "late": 4, "absent": 2, "avgHrs": "8.1"}),
    Row("Nina", "Brooks", "nina.brooks@company.com", "+1 (555) 401-1104", Role.manager, "Marketing Manager", 131000, date(2020, 6, 15), "Marketing", pw("Nina", "Brooks"), "admin", dob=date(1989, 7, 29), attendance={"present": 224, "late": 3, "absent": 1, "avgHrs": "8.2"}),
    Row("Derek", "Vaughn", "derek.vaughn@company.com", "+1 (555) 401-1105", Role.manager, "Legal Lead", 148000, date(2018, 11, 5), "Legal", pw("Derek", "Vaughn"), "admin", dob=date(1983, 2, 11), attendance={"present": 232, "late": 2, "absent": 0, "avgHrs": "8.6"}),
    Row("Sierra", "Blake", "sierra.blake@company.com", "+1 (555) 401-1106", Role.manager, "Sales Director", 152000, date(2019, 2, 25), "Sales", pw("Sierra", "Blake"), "admin", dob=date(1986, 9, 3), attendance={"present": 218, "late": 5, "absent": 1, "avgHrs": "8.5"}),
    Row("Yuki", "Tanaka", "yuki.tanaka@company.com", "+1 (555) 401-1107", Role.manager, "Research Lead", 149000, date(2020, 4, 20), "Research", pw("Yuki", "Tanaka"), "admin", dob=date(1987, 12, 19), goals_completed="8 / 10", attendance={"present": 226, "late": 2, "absent": 1, "avgHrs": "8.4"}),
    Row("Carlos", "Mendez", "carlos.mendez@company.com", "+1 (555) 401-1108", Role.manager, "Operations Manager", 134000, date(2021, 3, 1), "Operations", pw("Carlos", "Mendez"), "admin", dob=date(1992, 5, 7), attendance={"present": 214, "late": 4, "absent": 2, "avgHrs": "8.0"}),
    Row("Hannah", "Irving", "hannah.irving@company.com", "+1 (555) 401-1109", Role.manager, "Design Lead", 136000, date(2021, 8, 16), "Design", pw("Hannah", "Irving"), "admin", dob=date(1991, 1, 26), attendance={"present": 210, "late": 3, "absent": 1, "avgHrs": "8.1"}),
]

# After managers exist, map manager email -> key for reports
MGR_EMAIL_TO_KEY: dict[str, str] = {
    "marcus.hale@company.com": "mgr_finance",
    "elena.park@company.com": "mgr_hr",
    "omar.farouk@company.com": "mgr_support",
    "nina.brooks@company.com": "mgr_marketing",
    "derek.vaughn@company.com": "mgr_legal",
    "sierra.blake@company.com": "mgr_sales",
    "yuki.tanaka@company.com": "mgr_research",
    "carlos.mendez@company.com": "mgr_operations",
    "hannah.irving@company.com": "mgr_design",
}


def ensure_department(db, name: str, code: str) -> Department:
    d = db.query(Department).filter(Department.name == name).first()
    if d:
        return d
    d = Department(name=name, code=code, is_active=True)
    db.add(d)
    db.commit()
    db.refresh(d)
    print(f"  + department: {name} ({code})")
    return d


def get_dept_id(db, name: str) -> int:
    d = db.query(Department).filter(Department.name == name).first()
    if not d:
        raise SystemExit(f"Department {name!r} not found. Create it or run main seed first.")
    return d.id


def ensure_employee(
    db,
    *,
    first: str,
    last: str,
    email: str,
    phone: str,
    role: Role,
    title: str,
    salary: float,
    started: date,
    manager_id: int | None,
    department_id: int,
    password: str,
    dob: Optional[date],
    rating: float,
    goals_completed: str,
    peer_reviews: int,
    attendance: dict[str, Any],
) -> tuple[bool, Employee]:
    """Returns (inserted?, employee)."""
    em = email.strip().lower()
    existing = db.query(Employee).filter(Employee.email == em).first()
    if existing:
        return False, existing

    initials = (first[:1] + last[:1]).upper()
    e = Employee(
        first=first,
        last=last,
        initials=initials,
        email=em,
        phone=phone,
        role=role,
        title=title,
        salary=float(salary),
        status="active",
        start=started,
        manager_id=manager_id,
        department_id=department_id,
        dob=dob,
        gender="Other",
        nationality="United States",
        marital="Single",
        address="Remote",
        emergency="—",
        rating=rating,
        goals_completed=goals_completed,
        peer_reviews=peer_reviews,
        attendance=attendance or {"present": 200, "late": 4, "absent": 1, "avgHrs": "8.2"},
        leave_balance={"annual": "14 / 20", "sick": "8 / 10", "personal": "3 / 5"},
    )
    db.add(e)
    db.flush()
    db.add(EmployeeCredential(employee_id=e.id, password_hash=hash_password(password)))
    db.commit()
    db.refresh(e)
    return True, e


def row_to_args(
    r: Row,
    manager_id: int | None,
    department_id: int,
) -> dict[str, Any]:
    return {
        "first": r.first,
        "last": r.last,
        "email": r.email,
        "phone": r.phone,
        "role": r.role,
        "title": r.title,
        "salary": r.salary,
        "started": r.started,
        "manager_id": manager_id,
        "department_id": department_id,
        "password": r.password,
        "dob": r.dob,
        "rating": r.rating,
        "goals_completed": r.goals_completed,
        "peer_reviews": r.peer_reviews,
        "attendance": r.attendance
        or {"present": 200, "late": 4, "absent": 1, "avgHrs": "8.2"},
    }


IC_ROWS: list[Row] = [
    Row("Aiden", "Frost", "aiden.frost@company.com", "+1 (555) 402-2201", Role.employee, "Staff Engineer", 124000, date(2022, 4, 11), "Engineering", pw("Aiden", "Frost"), "rita", goals_completed="7 / 10", attendance={"present": 216, "late": 4, "absent": 1, "avgHrs": "8.3"}),
    Row("Zoe", "Patel", "zoe.patel@company.com", "+1 (555) 402-2202", Role.employee, "Mobile Engineer", 116000, date(2023, 2, 27), "Engineering", pw("Zoe", "Patel"), "rita", attendance={"present": 198, "late": 5, "absent": 2, "avgHrs": "8.0"}),
    Row("Finn", "Doyle", "finn.doyle@company.com", "+1 (555) 402-2203", Role.employee, "Product Owner", 118000, date(2022, 8, 8), "Product", pw("Finn", "Doyle"), "tanya", attendance={"present": 208, "late": 4, "absent": 1, "avgHrs": "8.2"}),
    Row("Ivy", "Santos", "ivy.santos@company.com", "+1 (555) 402-2204", Role.employee, "Program Manager", 114000, date(2023, 6, 12), "Product", pw("Ivy", "Santos"), "tanya", attendance={"present": 192, "late": 6, "absent": 2, "avgHrs": "7.9"}),
    Row("Walter", "Cho", "walter.cho@company.com", "+1 (555) 402-2205", Role.employee, "Financial Analyst", 92000, date(2021, 10, 4), "Finance", pw("Walter", "Cho"), "mgr_finance", attendance={"present": 222, "late": 3, "absent": 1, "avgHrs": "8.2"}),
    Row("Greta", "Lind", "greta.lind@company.com", "+1 (555) 402-2206", Role.employee, "HR Specialist", 78000, date(2022, 1, 17), "Human Resources", pw("Greta", "Lind"), "mgr_hr", attendance={"present": 218, "late": 3, "absent": 2, "avgHrs": "8.1"}),
    Row("Rex", "Nolan", "rex.nolan@company.com", "+1 (555) 402-2207", Role.employee, "Support Engineer", 88000, date(2023, 3, 20), "Support", pw("Rex", "Nolan"), "mgr_support", attendance={"present": 204, "late": 5, "absent": 3, "avgHrs": "7.9"}),
    Row("Jade", "Porter", "jade.porter@company.com", "+1 (555) 402-2208", Role.employee, "Growth Marketer", 102000, date(2022, 5, 9), "Marketing", pw("Jade", "Porter"), "mgr_marketing", attendance={"present": 212, "late": 4, "absent": 2, "avgHrs": "8.0"}),
    Row("Beau", "Sterling", "beau.sterling@company.com", "+1 (555) 402-2209", Role.employee, "Paralegal", 87000, date(2023, 9, 5), "Legal", pw("Beau", "Sterling"), "mgr_legal", attendance={"present": 196, "late": 4, "absent": 1, "avgHrs": "8.0"}),
    Row("Tucker", "Wade", "tucker.wade@company.com", "+1 (555) 402-2210", Role.employee, "Account Executive", 98000, date(2022, 11, 14), "Sales", pw("Tucker", "Wade"), "mgr_sales", attendance={"present": 206, "late": 6, "absent": 2, "avgHrs": "8.3"}),
    Row("Ada", "Mueller", "ada.mueller@company.com", "+1 (555) 402-2211", Role.employee, "Research Scientist", 132000, date(2021, 7, 6), "Research", pw("Ada", "Mueller"), "mgr_research", goals_completed="6 / 10", attendance={"present": 224, "late": 2, "absent": 0, "avgHrs": "8.5"}),
    Row("Quinn", "Reeves", "quinn.reeves@company.com", "+1 (555) 402-2212", Role.employee, "Ops Coordinator", 76000, date(2023, 4, 24), "Operations", pw("Quinn", "Reeves"), "mgr_operations", attendance={"present": 188, "late": 5, "absent": 2, "avgHrs": "7.8"}),
    Row("Miles", "Orchard", "miles.orchard@company.com", "+1 (555) 402-2213", Role.employee, "Product Designer", 108000, date(2022, 2, 28), "Design", pw("Miles", "Orchard"), "mgr_design", attendance={"present": 214, "late": 3, "absent": 1, "avgHrs": "8.2"}),
]


def resolve_manager_id(key: str, ctx: dict[str, Employee | None]) -> int | None:
    if key == "admin":
        a = ctx.get("admin")
        return a.id if a else None
    if key == "rita":
        r = ctx.get("rita")
        return r.id if r else None
    if key == "tanya":
        t = ctx.get("tanya")
        return t.id if t else None
    m = ctx.get(key)
    return m.id if m else None


def main() -> None:
    db = SessionLocal()
    inserted = 0
    skipped = 0
    try:
        print("Ensuring new departments...")
        for name, code in NEW_DEPARTMENTS:
            ensure_department(db, name, code)

        admin = db.query(Employee).filter(Employee.role == Role.admin).order_by(Employee.id.asc()).first()
        if not admin:
            raise SystemExit("No admin user found (role=admin). Add one before running this script.")
        rita = db.query(Employee).filter(Employee.email == "rita.gomez@company.com").first()
        tanya = db.query(Employee).filter(Employee.email == "tanya.johnson@company.com").first()

        ctx: dict[str, Employee | None] = {
            "admin": admin,
            "rita": rita,
            "tanya": tanya,
        }

        print("Upserting managers...")
        for row in MANAGERS:
            dept_id = get_dept_id(db, row.dept_name)
            mid = resolve_manager_id(row.manager_key, ctx)
            if mid is None:
                print(f"  ! skip manager {row.email}: missing manager target {row.manager_key!r}")
                skipped += 1
                continue
            ok, _ = ensure_employee(db, **row_to_args(row, mid, dept_id))
            if ok:
                inserted += 1
                print(f"  + manager {row.email}")
            else:
                skipped += 1
                print(f"  = exists {row.email}")

        # Reload managers by email for IC reporting lines
        for em, key in MGR_EMAIL_TO_KEY.items():
            m = db.query(Employee).filter(Employee.email == em).first()
            ctx[key] = m
            if not m:
                print(f"  ! warning: manager {em} not found — reports keyed {key} will fail")

        print("Upserting individual contributors...")
        for row in IC_ROWS:
            dept_id = get_dept_id(db, row.dept_name)
            mid = resolve_manager_id(row.manager_key, ctx)
            if mid is None:
                print(f"  ! skip IC {row.email}: missing manager for key {row.manager_key!r}")
                skipped += 1
                continue
            ok, _ = ensure_employee(db, **row_to_args(row, mid, dept_id))
            if ok:
                inserted += 1
                print(f"  + employee {row.email}")
            else:
                skipped += 1
                print(f"  = exists {row.email}")

        print(f"Done. inserted={inserted}, skipped(already present or blocked)={skipped}")
        print("database:", os.getenv("DATABASE_URL", "").split("@")[-1])
    finally:
        db.close()


if __name__ == "__main__":
    main()
