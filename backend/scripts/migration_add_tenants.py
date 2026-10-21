"""
Migration: Add multi-tenant architecture to existing HRMS database.
Works on PostgreSQL, SQLite, etc.

What this script does:
1. Creates new tables: tenants, platform_users, plans, subscriptions, platform_refresh_tokens
2. Adds tenant_id column to all existing tables (Postgres & SQLite compatible)
3. Creates Tenant #1 = "company 1" and assigns all existing data to it
4. Migrates or creates alaa.saleem & admin@platform.corp in platform_users
5. Creates default plans and subscriptions

Run:
    docker exec hrms-api-1 python scripts/migration_add_tenants.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from app.database import engine, Base
from app.models import (
    AuditEvent, BlackoutDate, ChatMessage, Department, DepartmentFeatureFlag,
    Employee, EmployeeCredential, EmployeeDocument, LeaveAccrualLedger,
    LeavePolicy, LeaveRequest, Notification, Plan, PlatformRefreshToken,
    PlatformRole, PlatformUser, RefreshToken, Role, Subscription,
    SubscriptionStatus, Task, Tenant, TenantStatus,
)
from app.security import hash_password

print("=" * 60)
print("HRMS Multi-Tenant Migration")
print("=" * 60)

# ------------------------------------------------------------------
# Step 1: Create all new tables (Tenant, PlatformUser, Plan, etc.)
# ------------------------------------------------------------------
print("\n[1/6] Creating new schema tables...")
Base.metadata.create_all(engine)
print("      ✓ Schema up to date")

with Session(engine) as db:

    # ------------------------------------------------------------------
    # Step 2: Create the default Starter & Pro & Enterprise plans
    # ------------------------------------------------------------------
    print("\n[2/6] Creating default plans...")
    starter = db.query(Plan).filter(Plan.name == "Starter").first()
    if not starter:
        starter = Plan(
            name="Starter",
            price_usd=19.0,
            max_employees=50,
            max_storage_mb=5120,
            features={"employees": True, "departments": True, "leaves": True, "tasks": True},
            is_active=True,
        )
        db.add(starter)
        db.flush()
        print("      ✓ Plan 'Starter' created")

    pro = db.query(Plan).filter(Plan.name == "Pro").first()
    if not pro:
        pro = Plan(
            name="Pro",
            price_usd=49.0,
            max_employees=250,
            max_storage_mb=51200,
            features={"employees": True, "departments": True, "leaves": True, "tasks": True, "payroll": True, "performance": True, "reports": True},
            is_active=True,
        )
        db.add(pro)
        db.flush()
        print("      ✓ Plan 'Pro' created")

    # ------------------------------------------------------------------
    # Step 3: Create Tenant #1
    # ------------------------------------------------------------------
    print("\n[3/6] Creating Tenant #1 — 'company 1'...")
    tenant = db.query(Tenant).filter(Tenant.slug == "company-1").first()
    if not tenant:
        tenant = Tenant(
            name="company 1",
            slug="company-1",
            status=TenantStatus.active,
            plan_id=starter.id,
            owner_email="ceo1@company1.corp",
        )
        db.add(tenant)
        db.flush()
        print(f"      ✓ Tenant 'company 1' created (id={tenant.id})")
    else:
        print(f"      ✓ Tenant 'company 1' already exists (id={tenant.id})")

    sub = db.query(Subscription).filter(Subscription.tenant_id == tenant.id).first()
    if not sub:
        sub = Subscription(
            tenant_id=tenant.id,
            plan_id=starter.id,
            status=SubscriptionStatus.active,
            current_period_end=datetime.now(timezone.utc) + timedelta(days=365),
        )
        db.add(sub)
        db.flush()
        print("      ✓ Subscription created for tenant")

    tenant_id = tenant.id
    db.commit()

# ------------------------------------------------------------------
# Step 4: Add tenant_id column across all tables (engine agnostic)
# ------------------------------------------------------------------
print(f"\n[4/6] Migrating columns to tenant_id={tenant_id}...")

tables_needing_tenant = [
    "departments", "employees", "tasks", "leave_requests",
    "notifications", "chat_messages", "leave_policies",
    "audit_events", "department_feature_flags", "blackout_dates",
    "leave_accrual_ledger", "employee_documents",
]

is_postgres = "postgresql" in str(engine.url)

with engine.connect() as conn:
    for table in tables_needing_tenant:
        try:
            if is_postgres:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);"))
                conn.execute(text(f"UPDATE {table} SET tenant_id = :tid WHERE tenant_id IS NULL;"), {"tid": tenant_id})
                conn.commit()
                print(f"      ✓ {table}.tenant_id ready")
            else:
                # SQLite
                insp = inspect(engine)
                cols = [c["name"] for c in insp.get_columns(table)]
                if "tenant_id" not in cols:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN tenant_id INTEGER;"))
                conn.execute(text(f"UPDATE {table} SET tenant_id = :tid WHERE tenant_id IS NULL;"), {"tid": tenant_id})
                conn.commit()
                print(f"      ✓ {table}.tenant_id ready")
        except Exception as e:
            print(f"      ! {table}: {e}")

print("      ✓ tenant_id migration complete")

# ------------------------------------------------------------------
# Step 5: Setup platform_users (alaa.saleem & admin@platform.corp)
# ------------------------------------------------------------------
print("\n[5/6] Creating / updating platform users...")

with Session(engine) as db:
    users_to_seed = [
        {"email": "alaa.saleem@platform.corp", "name": "Alaa Saleem", "pw": "alaa.alaa.12", "role": PlatformRole.super_admin},
        {"email": "admin@platform.corp", "name": "Super Admin", "pw": "admin@123", "role": PlatformRole.super_admin},
        {"email": "support@platform.corp", "name": "Support Agent", "pw": "support@123", "role": PlatformRole.support_agent},
        {"email": "billing@platform.corp", "name": "Billing Admin", "pw": "billing@123", "role": PlatformRole.billing_admin},
    ]

    for u in users_to_seed:
        pu = db.query(PlatformUser).filter(PlatformUser.email == u["email"]).first()
        if not pu:
            pu = PlatformUser(
                email=u["email"],
                password_hash=hash_password(u["pw"]),
                platform_role=u["role"],
                full_name=u["name"],
                is_active=True,
            )
            db.add(pu)
            db.flush()
            print(f"      ✓ Created PlatformUser: {u['email']} (role={u['role'].value})")
        else:
            print(f"      ✓ PlatformUser already exists: {u['email']}")

    db.commit()

# ------------------------------------------------------------------
# Step 6: Verify
# ------------------------------------------------------------------
print("\n[6/6] Verification...")
with Session(engine) as db:
    tenants = db.query(Tenant).all()
    pus = db.query(PlatformUser).all()
    emps = db.query(Employee).all()
    plans = db.query(Plan).all()

    print(f"      Tenants:        {len(tenants)}")
    print(f"      Platform Users: {len(pus)}")
    print(f"      Employees:      {len(emps)}")
    print(f"      Plans:          {len(plans)}")

    for t in tenants:
        emp_cnt = db.query(Employee).filter(Employee.tenant_id == t.id).count()
        print(f"      - Tenant [{t.id}] '{t.name}': {emp_cnt} employees, status={t.status.value}")

    for pu in pus:
        print(f"      - PlatformUser: {pu.email} ({pu.platform_role.value})")

print("\n" + "=" * 60)
print("Migration complete!")
print("=" * 60)
print("\nPlatform Admin Login:")
print("  Email:    admin@platform.corp  (or alaa.saleem@platform.corp)")
print("  Password: admin@123           (or alaa.alaa.12)")
print("  URL:      http://127.0.0.1:8000/platform-admin.html")
