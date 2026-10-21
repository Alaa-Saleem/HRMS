"""Platform → Statistics dashboard data."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func

from app.deps import CurrentPlatformUser, DbSession
from app.models import (
    AuditEvent, Employee, PlatformUser, Subscription,
    SubscriptionStatus, Tenant, TenantStatus,
)

router = APIRouter(prefix="/platform/stats", tags=["platform-stats"])


@router.get("", response_model=dict)
def platform_stats(db: DbSession, user: CurrentPlatformUser):
    total_tenants   = db.query(func.count(Tenant.id)).scalar() or 0
    active_tenants  = db.query(func.count(Tenant.id)).filter(Tenant.status == TenantStatus.active).scalar() or 0
    trial_tenants   = db.query(func.count(Tenant.id)).filter(Tenant.status == TenantStatus.trial).scalar() or 0
    suspended_tenants = db.query(func.count(Tenant.id)).filter(Tenant.status == TenantStatus.suspended).scalar() or 0
    total_employees = db.query(func.count(Employee.id)).scalar() or 0
    total_platform_users = db.query(func.count(PlatformUser.id)).scalar() or 0
    active_subscriptions = db.query(func.count(Subscription.id)).filter(
        Subscription.status.in_([SubscriptionStatus.active, SubscriptionStatus.trial])
    ).scalar() or 0

    # Recent audit events (last 10)
    recent_events = db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(10).all()
    recent_list = [
        {
            "id": e.id,
            "action": e.action,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "tenant_id": e.tenant_id,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in recent_events
    ]

    # Tenant breakdown (top 10 by employee count)
    tenant_breakdown = (
        db.query(Tenant.id, Tenant.name, Tenant.status, func.count(Employee.id).label("emp_count"))
        .outerjoin(Employee, Employee.tenant_id == Tenant.id)
        .group_by(Tenant.id)
        .order_by(func.count(Employee.id).desc())
        .limit(10)
        .all()
    )

    return {
        "tenants": {
            "total": total_tenants,
            "active": active_tenants,
            "trial": trial_tenants,
            "suspended": suspended_tenants,
        },
        "employees": {"total": total_employees},
        "platform_users": {"total": total_platform_users},
        "subscriptions": {"active": active_subscriptions},
        "recent_audit_events": recent_list,
        "top_tenants_by_employees": [
            {
                "id": r.id,
                "name": r.name,
                "status": r.status.value,
                "employee_count": r.emp_count,
            }
            for r in tenant_breakdown
        ],
    }
