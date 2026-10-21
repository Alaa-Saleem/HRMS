"""Platform → Subscriptions management.

All endpoints require a valid platform JWT.
Super admin can create/modify subscriptions; support/billing can view.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.deps import CurrentPlatformUser, DbSession
from app.models import (
    AuditEvent, Plan, PlatformRole, Subscription,
    SubscriptionStatus, Tenant,
)

router = APIRouter(prefix="/platform/subscriptions", tags=["platform-subscriptions"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_super_or_billing(user):
    if user.platform_role not in (PlatformRole.super_admin, PlatformRole.billing_admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Super admin or billing admin only")


def _sub_row(s: Subscription) -> dict:
    return {
        "id": s.id,
        "tenant_id": s.tenant_id,
        "tenant_name": s.tenant.name if s.tenant else "—",
        "tenant_slug": s.tenant.slug if s.tenant else "—",
        "plan_id": s.plan_id,
        "plan_name": s.plan.name if s.plan else "—",
        "plan_price": s.plan.price_usd if s.plan else 0,
        "status": s.status.value,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
        "cancelled_at": s.cancelled_at.isoformat() if s.cancelled_at else None,
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SubscriptionCreate(BaseModel):
    tenant_id: int
    plan_id: int
    status: SubscriptionStatus = SubscriptionStatus.trial
    current_period_end: Optional[datetime] = None


class SubscriptionUpdate(BaseModel):
    plan_id: Optional[int] = None
    status: Optional[SubscriptionStatus] = None
    current_period_end: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=dict)
def list_subscriptions(
    db: DbSession,
    user: CurrentPlatformUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    tenant_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    q = db.query(Subscription)
    if status_filter:
        try:
            q = q.filter(Subscription.status == SubscriptionStatus(status_filter))
        except ValueError:
            pass
    if tenant_id is not None:
        q = q.filter(Subscription.tenant_id == tenant_id)

    total = q.count()
    subs = (
        q.order_by(Subscription.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_sub_row(s) for s in subs],
    }


@router.get("/{sub_id}", response_model=dict)
def get_subscription(sub_id: int, db: DbSession, user: CurrentPlatformUser):
    s = db.get(Subscription, sub_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subscription not found")
    return _sub_row(s)


@router.post("", response_model=dict, status_code=201)
def create_subscription(db: DbSession, user: CurrentPlatformUser, body: SubscriptionCreate):
    _require_super_or_billing(user)

    tenant = db.get(Tenant, body.tenant_id)
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    plan = db.get(Plan, body.plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")

    sub = Subscription(
        tenant_id=body.tenant_id,
        plan_id=body.plan_id,
        status=body.status,
        current_period_end=body.current_period_end,
    )
    db.add(sub)
    db.flush()

    db.add(AuditEvent(
        actor_platform_user_id=user.id,
        action="platform.subscription.created",
        entity_type="subscription",
        entity_id=sub.id,
        payload={"tenant_id": body.tenant_id, "plan_id": body.plan_id, "status": body.status.value},
    ))
    db.commit()
    return _sub_row(sub)


@router.patch("/{sub_id}", response_model=dict)
def update_subscription(sub_id: int, db: DbSession, user: CurrentPlatformUser, body: SubscriptionUpdate):
    _require_super_or_billing(user)
    s = db.get(Subscription, sub_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subscription not found")

    if body.plan_id is not None:
        plan = db.get(Plan, body.plan_id)
        if not plan:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")
        s.plan_id = body.plan_id
    if body.status is not None:
        s.status = body.status
        if body.status == SubscriptionStatus.cancelled and not s.cancelled_at:
            s.cancelled_at = datetime.now(timezone.utc)
    if body.current_period_end is not None:
        s.current_period_end = body.current_period_end

    db.add(AuditEvent(
        actor_platform_user_id=user.id,
        action="platform.subscription.updated",
        entity_type="subscription",
        entity_id=s.id,
        payload={"new_status": s.status.value if s.status else None},
    ))
    db.commit()
    return _sub_row(s)


@router.delete("/{sub_id}", response_model=dict)
def cancel_subscription(sub_id: int, db: DbSession, user: CurrentPlatformUser):
    _require_super_or_billing(user)
    s = db.get(Subscription, sub_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subscription not found")

    s.status = SubscriptionStatus.cancelled
    s.cancelled_at = datetime.now(timezone.utc)
    db.add(AuditEvent(
        actor_platform_user_id=user.id,
        action="platform.subscription.cancelled",
        entity_type="subscription",
        entity_id=s.id,
    ))
    db.commit()
    return {"ok": True, "subscription_id": sub_id}
