#!/usr/bin/env python3
"""
Seed platform users (super_admin, support_agent, billing_admin)
into the database. Safe to run multiple times — skips existing emails.

Usage (from backend/ directory):
    DATABASE_URL=postgresql://hrms:hrms@localhost:5433/hrms python scripts/seed_platform.py
    # or with Docker:
    docker compose exec api python scripts/seed_platform.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models import Plan, PlatformUser, PlatformRole, Subscription, SubscriptionStatus, Tenant, TenantStatus  # noqa: E402
from app.security import hash_password  # noqa: E402


PLATFORM_USERS = [
    {
        "email": "admin@platform.corp",
        "password": "admin@123",
        "full_name": "Super Admin",
        "platform_role": PlatformRole.super_admin,
    },
    {
        "email": "support@platform.corp",
        "password": "support@123",
        "full_name": "Support Agent",
        "platform_role": PlatformRole.support_agent,
    },
    {
        "email": "billing@platform.corp",
        "password": "billing@123",
        "full_name": "Billing Admin",
        "platform_role": PlatformRole.billing_admin,
    },
]

SAMPLE_PLANS = [
    {
        "name": "Starter",
        "price_usd": 19.0,
        "max_employees": 50,
        "max_storage_mb": 5120,
        "features": {"employees": True, "departments": True, "leaves": True, "tasks": True,
                     "payroll": False, "performance": False, "reports": False, "api": False},
    },
    {
        "name": "Pro",
        "price_usd": 49.0,
        "max_employees": 250,
        "max_storage_mb": 51200,
        "features": {"employees": True, "departments": True, "leaves": True, "tasks": True,
                     "payroll": True, "performance": True, "reports": True, "api": False},
    },
    {
        "name": "Enterprise",
        "price_usd": 0.0,
        "max_employees": 999999,
        "max_storage_mb": 524288,
        "features": {"employees": True, "departments": True, "leaves": True, "tasks": True,
                     "payroll": True, "performance": True, "reports": True, "api": True, "sso": True},
    },
]


def main() -> None:
    db = SessionLocal()
    try:
        # ── Platform Users ────────────────────────────────────────
        created_users = 0
        for u in PLATFORM_USERS:
            existing = db.query(PlatformUser).filter(PlatformUser.email == u["email"]).first()
            if existing:
                print(f"  [skip] platform user already exists: {u['email']}")
                continue
            pu = PlatformUser(
                email=u["email"],
                password_hash=hash_password(u["password"]),
                full_name=u["full_name"],
                platform_role=u["platform_role"],
                is_active=True,
            )
            db.add(pu)
            created_users += 1
            print(f"  [+] Created platform user: {u['email']} ({u['platform_role'].value})")

        # ── Plans ─────────────────────────────────────────────────
        created_plans = 0
        plan_ids = {}
        for p in SAMPLE_PLANS:
            existing = db.query(Plan).filter(Plan.name == p["name"]).first()
            if existing:
                plan_ids[p["name"]] = existing.id
                print(f"  [skip] plan already exists: {p['name']}")
                continue
            plan = Plan(
                name=p["name"],
                price_usd=p["price_usd"],
                max_employees=p["max_employees"],
                max_storage_mb=p["max_storage_mb"],
                features=p["features"],
                is_active=True,
            )
            db.add(plan)
            db.flush()
            plan_ids[p["name"]] = plan.id
            created_plans += 1
            print(f"  [+] Created plan: {p['name']} (${p['price_usd']}/mo)")

        # ── Demo Tenants ──────────────────────────────────────────
        demo_tenants = [
            {"name": "Acme Corporation", "slug": "acme-corp", "status": TenantStatus.active, "plan": "Pro", "owner_email": "admin@acme.corp"},
            {"name": "Tech Palestine", "slug": "tech-palestine", "status": TenantStatus.trial, "plan": "Starter", "owner_email": "ceo@techpal.ps"},
            {"name": "Al-Rashid Group", "slug": "alrashid-group", "status": TenantStatus.active, "plan": "Enterprise", "owner_email": "admin@alrashid.sa"},
        ]
        created_tenants = 0
        for t_data in demo_tenants:
            existing = db.query(Tenant).filter(Tenant.slug == t_data["slug"]).first()
            if existing:
                print(f"  [skip] tenant already exists: {t_data['slug']}")
                continue
            plan_id = plan_ids.get(t_data["plan"])
            tenant = Tenant(
                name=t_data["name"],
                slug=t_data["slug"],
                status=t_data["status"],
                plan_id=plan_id,
                owner_email=t_data["owner_email"],
            )
            db.add(tenant)
            db.flush()

            # Create a subscription for this tenant
            if plan_id:
                sub_status = SubscriptionStatus.active if t_data["status"] == TenantStatus.active else SubscriptionStatus.trial
                db.add(Subscription(
                    tenant_id=tenant.id,
                    plan_id=plan_id,
                    status=sub_status,
                ))

            created_tenants += 1
            print(f"  [+] Created tenant: {t_data['name']} ({t_data['status'].value})")

        db.commit()
        print(f"\nPlatform seed complete:")
        print(f"  Users created:   {created_users}")
        print(f"  Plans created:   {created_plans}")
        print(f"  Tenants created: {created_tenants}")
        print()
        print("Login credentials:")
        for u in PLATFORM_USERS:
            print(f"  {u['email']}  /  {u['password']}  ({u['platform_role'].value})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
