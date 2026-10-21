"""Platform → Plans management."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.deps import CurrentPlatformUser, DbSession
from app.models import Plan, PlatformRole

router = APIRouter(prefix="/platform/plans", tags=["platform-plans"])


def _require_super_admin(user):
    if user.platform_role != PlatformRole.super_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Super admin only")


def _plan_row(p: Plan) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "price_usd": p.price_usd,
        "max_employees": p.max_employees,
        "max_storage_mb": p.max_storage_mb,
        "features": p.features,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


class PlanCreate(BaseModel):
    name: str
    price_usd: float = 0.0
    max_employees: int = 50
    max_storage_mb: int = 500
    features: dict[str, Any] = {}


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    price_usd: Optional[float] = None
    max_employees: Optional[int] = None
    max_storage_mb: Optional[int] = None
    features: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


@router.get("", response_model=list)
def list_plans(db: DbSession, user: CurrentPlatformUser):
    plans = db.query(Plan).order_by(Plan.price_usd).all()
    return [_plan_row(p) for p in plans]


@router.post("", response_model=dict, status_code=201)
def create_plan(db: DbSession, user: CurrentPlatformUser, body: PlanCreate):
    _require_super_admin(user)
    plan = Plan(
        name=body.name,
        price_usd=body.price_usd,
        max_employees=body.max_employees,
        max_storage_mb=body.max_storage_mb,
        features=body.features,
    )
    db.add(plan)
    db.commit()
    return _plan_row(plan)


@router.patch("/{plan_id}", response_model=dict)
def update_plan(plan_id: int, db: DbSession, user: CurrentPlatformUser, body: PlanUpdate):
    _require_super_admin(user)
    p = db.get(Plan, plan_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")
    if body.name is not None:          p.name = body.name
    if body.price_usd is not None:     p.price_usd = body.price_usd
    if body.max_employees is not None: p.max_employees = body.max_employees
    if body.max_storage_mb is not None: p.max_storage_mb = body.max_storage_mb
    if body.features is not None:      p.features = body.features
    if body.is_active is not None:     p.is_active = body.is_active
    db.commit()
    return _plan_row(p)
