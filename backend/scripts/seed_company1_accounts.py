#!/usr/bin/env python3
"""
Seed company 1 accounts into the database for Tenant #1.
Idempotent: skips existing emails.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal
from app.models import Department, Employee, EmployeeCredential, Role, Tenant
from app.security import hash_password

COMPANY1_ROSTER = [
    # Administrators
    {"first": "CEO", "last": "One", "email": "ceo1@company1.corp", "role": Role.admin, "title": "الرئيس التنفيذي (CEO)", "salary": 220000, "password": "admin@123", "dept_code": "EXC"},
    {"first": "HR", "last": "Manager", "email": "hrmanager1@company1.corp", "role": Role.admin, "title": "مدير الموارد البشرية", "salary": 160000, "password": "admin@123", "dept_code": "HRM"},
    {"first": "Financial", "last": "Manager", "email": "financialmanager1@company1.corp", "role": Role.manager, "title": "المدير المالي", "salary": 150000, "password": "admin@123", "dept_code": "FIN"},
    {"first": "Tech", "last": "Manager", "email": "tech1@company1.corp", "role": Role.admin, "title": "المدير التقني (CTO)", "salary": 170000, "password": "admin@123", "dept_code": "ENG"},
    {"first": "Product", "last": "Manager", "email": "product1@company1.corp", "role": Role.manager, "title": "مدير المنتجات", "salary": 140000, "password": "admin@123", "dept_code": "PRD"},
    {"first": "Operations", "last": "Manager", "email": "operations1@company1.corp", "role": Role.manager, "title": "مدير العمليات", "salary": 135000, "password": "admin@123", "dept_code": "OPS"},
    {"first": "Marketing", "last": "Manager", "email": "marketing1@company1.corp", "role": Role.manager, "title": "مدير التسويق", "salary": 130000, "password": "admin@123", "dept_code": "MKT"},
    {"first": "Sales", "last": "Manager", "email": "sales1@company1.corp", "role": Role.manager, "title": "مدير المبيعات", "salary": 145000, "password": "admin@123", "dept_code": "SLS"},

    # Employees
    {"first": "Employee", "last": "One", "email": "emp1.1@company1.corp", "role": Role.employee, "title": "مهندس برمجيات", "salary": 95000, "password": "user@123", "dept_code": "ENG"},
    {"first": "Employee", "last": "Two", "email": "emp1.2@company1.corp", "role": Role.employee, "title": "أخصائي موارد بشرية", "salary": 85000, "password": "user@123", "dept_code": "HRM"},
    {"first": "Employee", "last": "Three", "email": "emp1.3@company1.corp", "role": Role.employee, "title": "محاسب مالي", "salary": 90000, "password": "user@123", "dept_code": "FIN"},
    {"first": "Employee", "last": "Four", "email": "emp1.4@company1.corp", "role": Role.employee, "title": "مصمم واجهات UX/UI", "salary": 92000, "password": "user@123", "dept_code": "PRD"},
    {"first": "Employee", "last": "Five", "email": "emp1.5@company1.corp", "role": Role.employee, "title": "منسق عمليات", "salary": 80000, "password": "user@123", "dept_code": "OPS"},
]


def main():
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "company-1").first()
        if not tenant:
            tenant = db.query(Tenant).first()
        tenant_id = tenant.id if tenant else 1

        # Map departments
        depts = db.query(Department).all()
        dept_map = {d.code: d.id for d in depts if d.code}
        default_dept_id = depts[0].id if depts else None

        created = 0
        for item in COMPANY1_ROSTER:
            email = item["email"].lower()
            existing = db.query(Employee).filter(Employee.email == email).first()
            if existing:
                continue

            dept_id = dept_map.get(item["dept_code"], default_dept_id)
            emp = Employee(
                first=item["first"],
                last=item["last"],
                initials=(item["first"][:1] + item["last"][:1]).upper(),
                email=email,
                phone="+966 50 000 0000",
                role=item["role"],
                title=item["title"],
                salary=float(item["salary"]),
                status="active",
                start=date(2022, 1, 1),
                tenant_id=tenant_id,
                department_id=dept_id,
                rating=4.8,
                goals_completed="8 / 10",
                peer_reviews=5,
                attendance={"present": 240, "late": 1, "absent": 0, "avgHrs": "8.5"},
                leave_balance={"annual": "20 / 30", "sick": "15 / 15", "personal": "5 / 5"},
            )
            db.add(emp)
            db.flush()

            db.add(EmployeeCredential(
                employee_id=emp.id,
                password_hash=hash_password(item["password"])
            ))
            created += 1
            print(f"  ✓ Created: {email} ({item['role'].value})")

        db.commit()
        print(f"\nDone. Created {created} company1 accounts.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
