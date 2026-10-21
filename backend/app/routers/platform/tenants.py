"""Platform → Tenant management endpoints.

All endpoints require a valid platform JWT (super_admin or support_agent).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func

from app.deps import CurrentPlatformUser, DbSession
from app.models import (
    AuditEvent, Department, Employee, EmployeeCredential, Plan,
    PlatformRole, PlatformUser, Role, Subscription,
    SubscriptionStatus, Tenant, TenantStatus,
)
from app.security import create_access_token, hash_password

router = APIRouter(prefix="/platform/tenants", tags=["platform-tenants"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TenantCreate(BaseModel):
    name: str
    slug: str
    owner_email: Optional[str] = None
    plan_id: Optional[int] = None
    status: TenantStatus = TenantStatus.trial
    admin_name: Optional[str] = None
    admin_email: Optional[str] = None
    admin_password: Optional[str] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    owner_email: Optional[str] = None
    plan_id: Optional[int] = None
    status: Optional[TenantStatus] = None
    suspended_reason: Optional[str] = None


class TenantSuspend(BaseModel):
    reason: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_super_admin(user):
    if user.platform_role != PlatformRole.super_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Super admin only")


def _tenant_row(t: Tenant, db) -> dict:
    emp_count = db.query(func.count(Employee.id)).filter(Employee.tenant_id == t.id).scalar() or 0
    dept_count = db.query(func.count(Department.id)).filter(Department.tenant_id == t.id).scalar() or 0
    sub = db.query(Subscription).filter(
        Subscription.tenant_id == t.id,
        Subscription.status.in_([SubscriptionStatus.active, SubscriptionStatus.trial])
    ).order_by(Subscription.started_at.desc()).first()

    return {
        "id": t.id,
        "name": t.name,
        "slug": t.slug,
        "status": t.status.value,
        "plan_id": t.plan_id,
        "owner_email": t.owner_email,
        "suspended_reason": t.suspended_reason,
        "trial_ends_at": t.trial_ends_at.isoformat() if t.trial_ends_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "employee_count": emp_count,
        "department_count": dept_count,
        "subscription_status": sub.status.value if sub else None,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=dict)
def list_tenants(
    db: DbSession,
    user: CurrentPlatformUser,
    search: str = Query(""),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    q = db.query(Tenant)
    if search:
        q = q.filter(Tenant.name.ilike(f"%{search}%") | Tenant.slug.ilike(f"%{search}%"))
    if status_filter:
        try:
            q = q.filter(Tenant.status == TenantStatus(status_filter))
        except ValueError:
            pass

    total = q.count()
    tenants = q.order_by(Tenant.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_tenant_row(t, db) for t in tenants],
    }


@router.get("/{tenant_id}", response_model=dict)
def get_tenant(tenant_id: int, db: DbSession, user: CurrentPlatformUser):
    t = db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    return _tenant_row(t, db)


@router.get("/{tenant_id}/detail", response_model=dict)
def get_tenant_detail(tenant_id: int, db: DbSession, user: CurrentPlatformUser):
    """Full tenant detail including stats, subscription, and recent activity."""
    t = db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")

    emp_count  = db.query(func.count(Employee.id)).filter(Employee.tenant_id == t.id).scalar() or 0
    dept_count = db.query(func.count(Department.id)).filter(Department.tenant_id == t.id).scalar() or 0
    admin_count = db.query(func.count(Employee.id)).filter(
        Employee.tenant_id == t.id,
        Employee.role == "admin",
    ).scalar() or 0
    manager_count = db.query(func.count(Employee.id)).filter(
        Employee.tenant_id == t.id,
        Employee.role == "manager",
    ).scalar() or 0

    # Active subscription
    sub = db.query(Subscription).filter(
        Subscription.tenant_id == t.id,
        Subscription.status.in_([SubscriptionStatus.active, SubscriptionStatus.trial]),
    ).order_by(Subscription.started_at.desc()).first()

    plan = db.get(Plan, t.plan_id) if t.plan_id else None

    # Recent audit events for this tenant (last 20)
    recent_events = (
        db.query(AuditEvent)
        .filter(AuditEvent.tenant_id == t.id)
        .order_by(AuditEvent.created_at.desc())
        .limit(20)
        .all()
    )

    pu_ids = {e.actor_platform_user_id for e in recent_events if e.actor_platform_user_id}
    pus = {p.id: p for p in db.query(PlatformUser).filter(PlatformUser.id.in_(pu_ids)).all()} if pu_ids else {}

    def _actor(ev: AuditEvent) -> str:
        if ev.actor_platform_user_id and ev.actor_platform_user_id in pus:
            pu = pus[ev.actor_platform_user_id]
            return f"[Platform] {pu.full_name or pu.email}"
        return "System"

    # All subscriptions history
    all_subs = db.query(Subscription).filter(
        Subscription.tenant_id == t.id,
    ).order_by(Subscription.started_at.desc()).all()

    return {
        **_tenant_row(t, db),
        "stats": {
            "employee_count": emp_count,
            "department_count": dept_count,
            "admin_count": admin_count,
            "manager_count": manager_count,
        },
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "price_usd": plan.price_usd,
            "max_employees": plan.max_employees,
            "max_storage_mb": plan.max_storage_mb,
            "features": plan.features,
        } if plan else None,
        "active_subscription": {
            "id": sub.id,
            "status": sub.status.value,
            "plan_id": sub.plan_id,
            "plan_name": sub.plan.name if sub.plan else "—",
            "started_at": sub.started_at.isoformat() if sub.started_at else None,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        } if sub else None,
        "subscription_history": [
            {
                "id": s.id,
                "plan_name": s.plan.name if s.plan else f"Plan #{s.plan_id}",
                "status": s.status.value,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
                "cancelled_at": s.cancelled_at.isoformat() if s.cancelled_at else None,
            }
            for s in all_subs
        ],
        "recent_activity": [
            {
                "id": ev.id,
                "action": ev.action,
                "entity_type": ev.entity_type,
                "entity_id": ev.entity_id,
                "actor": _actor(ev),
                "ip": ev.ip,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            }
            for ev in recent_events
        ],
    }



@router.post("", response_model=dict, status_code=201)
def create_tenant(db: DbSession, user: CurrentPlatformUser, body: TenantCreate):
    _require_super_admin(user)

    # Check slug uniqueness
    slug = body.slug.strip().lower()
    existing = db.query(Tenant).filter(Tenant.slug == slug).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Slug '{slug}' already taken")

    owner_email = (body.admin_email or body.owner_email or "").strip().lower() or None

    tenant = Tenant(
        name=body.name.strip(),
        slug=slug,
        status=body.status,
        plan_id=body.plan_id,
        owner_email=owner_email,
    )
    db.add(tenant)
    db.flush()

    # 1. Auto-create default Department for the new company
    dept = Department(
        name="الإدارة العامة (General Management)",
        code="MGT",
        is_active=True,
        tenant_id=tenant.id,
    )
    db.add(dept)
    db.flush()

    # 2. Auto-create initial Admin Employee if email or password provided
    admin_created = False
    if owner_email or body.admin_password:
        admin_email = owner_email or f"admin@{slug}.corp"
        admin_pw = body.admin_password or "admin@123"
        admin_name = (body.admin_name or "").strip() or "مسؤول الشركة"
        name_parts = admin_name.split(maxsplit=1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else "الإدارة"

        emp = Employee(
            first=first_name,
            last=last_name,
            initials=(first_name[:1] + last_name[:1]).upper(),
            email=admin_email,
            phone="+966 50 000 0000",
            role=Role.admin,
            title="المدير العام / المسؤول التنفيذي (Company Admin)",
            salary=120000.0,
            status="active",
            start=date.today(),
            tenant_id=tenant.id,
            department_id=dept.id,
            rating=5.0,
            goals_completed="10 / 10",
            peer_reviews=5,
            attendance={"present": 240, "late": 0, "absent": 0, "avgHrs": "8.5"},
            leave_balance={"annual": "30 / 30", "sick": "15 / 15", "personal": "5 / 5"},
        )
        db.add(emp)
        db.flush()

        db.add(EmployeeCredential(
            employee_id=emp.id,
            password_hash=hash_password(admin_pw),
        ))
        admin_created = True

    # 3. Auto-create Subscription if plan_id is provided
    if body.plan_id:
        sub_status = SubscriptionStatus.active if body.status == TenantStatus.active else SubscriptionStatus.trial
        sub = Subscription(
            tenant_id=tenant.id,
            plan_id=body.plan_id,
            status=sub_status,
            current_period_end=datetime.now(timezone.utc) + timedelta(days=365),
        )
        db.add(sub)
        db.flush()

    # Audit
    db.add(AuditEvent(
        tenant_id=tenant.id,
        actor_platform_user_id=user.id,
        action="platform.tenant.created",
        entity_type="tenant",
        entity_id=tenant.id,
        payload={
            "name": body.name,
            "slug": slug,
            "owner_email": owner_email,
            "admin_created": admin_created,
            "plan_id": body.plan_id,
        },
    ))
    db.commit()
    return _tenant_row(tenant, db)


@router.patch("/{tenant_id}", response_model=dict)
def update_tenant(tenant_id: int, db: DbSession, user: CurrentPlatformUser, body: TenantUpdate):
    _require_super_admin(user)
    t = db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")

    if body.name is not None:      t.name = body.name
    if body.slug is not None:      t.slug = body.slug
    if body.owner_email is not None: t.owner_email = body.owner_email
    if body.plan_id is not None:   t.plan_id = body.plan_id
    if body.status is not None:    t.status = body.status
    if body.suspended_reason is not None: t.suspended_reason = body.suspended_reason

    db.add(AuditEvent(
        actor_platform_user_id=user.id,
        action="platform.tenant.updated",
        entity_type="tenant",
        entity_id=t.id,
    ))
    db.commit()
    return _tenant_row(t, db)


@router.post("/{tenant_id}/suspend", response_model=dict)
def suspend_tenant(tenant_id: int, db: DbSession, user: CurrentPlatformUser, body: TenantSuspend):
    _require_super_admin(user)
    t = db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")

    t.status = TenantStatus.suspended
    t.suspended_reason = body.reason
    db.add(AuditEvent(
        actor_platform_user_id=user.id,
        action="platform.tenant.suspended",
        entity_type="tenant",
        entity_id=t.id,
        payload={"reason": body.reason},
    ))
    db.commit()
    return {"ok": True, "tenant_id": t.id, "status": "suspended"}


@router.post("/{tenant_id}/activate", response_model=dict)
def activate_tenant(tenant_id: int, db: DbSession, user: CurrentPlatformUser):
    _require_super_admin(user)
    t = db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")

    t.status = TenantStatus.active
    t.suspended_reason = None
    db.add(AuditEvent(
        actor_platform_user_id=user.id,
        action="platform.tenant.activated",
        entity_type="tenant",
        entity_id=t.id,
    ))
    db.commit()
    return {"ok": True, "tenant_id": t.id, "status": "active"}


@router.delete("/{tenant_id}", response_model=dict)
def delete_tenant(tenant_id: int, db: DbSession, user: CurrentPlatformUser, confirm: bool = Query(False)):
    _require_super_admin(user)
    if not confirm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pass ?confirm=true to permanently delete a tenant")
    t = db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")

    db.add(AuditEvent(
        actor_platform_user_id=user.id,
        action="platform.tenant.deleted",
        entity_type="tenant",
        entity_id=t.id,
        payload={"name": t.name, "slug": t.slug},
    ))
    db.delete(t)
    db.commit()
    return {"ok": True, "deleted_tenant_id": tenant_id}


@router.post("/{tenant_id}/impersonate", response_model=dict)
def impersonate_tenant(tenant_id: int, db: DbSession, user: CurrentPlatformUser):
    """Super Admin impersonates tenant admin — issues a temporary token to log into the tenant's HRMS dashboard directly."""
    _require_super_admin(user)
    t = db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    if t.status == TenantStatus.suspended:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot impersonate a suspended tenant. Activate it first.")

    # Find admin or any employee belonging to this tenant
    emp = (
        db.query(Employee)
        .filter(Employee.tenant_id == t.id, Employee.role == Role.admin)
        .first()
    )
    if not emp:
        emp = db.query(Employee).filter(Employee.tenant_id == t.id).first()

    if not emp:
        # If tenant has no employees yet, create a default admin for impersonation
        dept = db.query(Department).filter(Department.tenant_id == t.id).first()
        if not dept:
            dept = Department(name="الإدارة العامة", code="MGT", tenant_id=t.id, is_active=True)
            db.add(dept)
            db.flush()

        emp_email = t.owner_email or f"admin@{t.slug}.corp"
        emp = Employee(
            first="مسؤول",
            last="الشركة",
            initials="MC",
            email=emp_email,
            phone="+966 50 000 0000",
            role=Role.admin,
            title="المدير العام (Company Admin)",
            salary=100000.0,
            status="active",
            start=date.today(),
            tenant_id=t.id,
            department_id=dept.id,
        )
        db.add(emp)
        db.flush()
        db.add(EmployeeCredential(employee_id=emp.id, password_hash=hash_password("admin@123")))

    # Generate employee JWT token for this tenant
    token = create_access_token({"sub": emp.email, "tenant_id": t.id})

    # Record Impersonation in Audit Log
    db.add(AuditEvent(
        tenant_id=t.id,
        actor_platform_user_id=user.id,
        action="platform.tenant.impersonated",
        entity_type="tenant",
        entity_id=t.id,
        payload={"impersonated_employee_email": emp.email, "tenant_name": t.name},
    ))
    db.commit()

    return {
        "ok": True,
        "access_token": token,
        "employee_email": emp.email,
        "tenant_id": t.id,
        "tenant_name": t.name,
        "redirect_url": "dashboard.html",
    }


@router.get("/{tenant_id}/employees", response_model=dict)
def get_tenant_employees(
    tenant_id: int,
    db: DbSession,
    user: CurrentPlatformUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """List all employees belonging to a specific tenant."""
    t = db.get(Tenant, tenant_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")

    q = db.query(Employee).filter(Employee.tenant_id == t.id)
    total = q.count()
    emps = (
        q.order_by(Employee.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "tenant_id": t.id,
        "tenant_name": t.name,
        "items": [
            {
                "id": e.id,
                "first": e.first,
                "last": e.last,
                "email": e.email,
                "role": e.role.value if hasattr(e.role, "value") else str(e.role),
                "title": e.title or "—",
                "department": e.department.name if e.department else "—",
                "status": e.status,
                "salary": e.salary,
                "start": e.start.isoformat() if e.start else None,
            }
            for e in emps
        ],
    }
