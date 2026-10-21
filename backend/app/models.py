from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Platform-level enums
# ---------------------------------------------------------------------------

class PlatformRole(str, enum.Enum):
    super_admin   = "super_admin"
    support_agent = "support_agent"
    billing_admin = "billing_admin"


class TenantStatus(str, enum.Enum):
    active    = "active"
    trial     = "trial"
    suspended = "suspended"
    cancelled = "cancelled"


class SubscriptionStatus(str, enum.Enum):
    active   = "active"
    trial    = "trial"
    past_due = "past_due"
    expired  = "expired"
    cancelled = "cancelled"


# ---------------------------------------------------------------------------
# Company-level enums (no more super_admin here — that lives in PlatformRole)
# ---------------------------------------------------------------------------

class Role(str, enum.Enum):
    admin    = "admin"
    manager  = "manager"
    employee = "employee"


class TaskStatus(str, enum.Enum):
    todo       = "todo"
    inprogress = "inprogress"
    done       = "done"


class LeaveStatus(str, enum.Enum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"


# ===========================================================================
# PLATFORM LAYER — completely separate from tenant data
# ===========================================================================

class Plan(Base):
    """Subscription plans (Starter, Pro, Enterprise …)."""
    __tablename__ = "plans"

    id:           Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:         Mapped[str]           = mapped_column(String(120), unique=True, nullable=False)
    price_usd:    Mapped[float]         = mapped_column(Float, default=0.0)
    max_employees: Mapped[int]          = mapped_column(Integer, default=50)
    max_storage_mb: Mapped[int]         = mapped_column(Integer, default=500)
    features:     Mapped[dict[str,Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_active:    Mapped[bool]          = mapped_column(Boolean, default=True)
    created_at:   Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenants:       Mapped[list["Tenant"]]       = relationship(back_populates="plan")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")


class Tenant(Base):
    """A subscribed company (one row = one isolated data silo)."""
    __tablename__ = "tenants"

    id:               Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:             Mapped[str]            = mapped_column(String(255), nullable=False)
    slug:             Mapped[str]            = mapped_column(String(120), unique=True, nullable=False, index=True)
    status:           Mapped[TenantStatus]   = mapped_column(
        Enum(TenantStatus, name="tenant_status_enum"), default=TenantStatus.trial, nullable=False
    )
    plan_id:          Mapped[Optional[int]]  = mapped_column(ForeignKey("plans.id"), nullable=True)
    owner_email:      Mapped[Optional[str]]  = mapped_column(String(255), nullable=True)
    suspended_reason: Mapped[Optional[str]]  = mapped_column(String(512), nullable=True)
    trial_ends_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:       Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:       Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    plan:          Mapped[Optional["Plan"]]          = relationship(back_populates="tenants")
    subscriptions: Mapped[list["Subscription"]]      = relationship(back_populates="tenant")
    departments:   Mapped[list["Department"]]        = relationship(back_populates="tenant")
    employees:     Mapped[list["Employee"]]          = relationship(back_populates="tenant")


class Subscription(Base):
    """Active subscription linking a tenant to a plan."""
    __tablename__ = "subscriptions"

    id:                 Mapped[int]                 = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id:          Mapped[int]                 = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id:            Mapped[int]                 = mapped_column(ForeignKey("plans.id"), nullable=False)
    status:             Mapped[SubscriptionStatus]  = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status_enum"), default=SubscriptionStatus.trial, nullable=False
    )
    current_period_end: Mapped[Optional[datetime]]  = mapped_column(DateTime(timezone=True), nullable=True)
    started_at:         Mapped[datetime]            = mapped_column(DateTime(timezone=True), server_default=func.now())
    cancelled_at:       Mapped[Optional[datetime]]  = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="subscriptions")
    plan:   Mapped["Plan"]   = relationship(back_populates="subscriptions")


class PlatformUser(Base):
    """Your own team members — completely separate from any tenant's employees."""
    __tablename__ = "platform_users"

    id:            Mapped[int]          = mapped_column(Integer, primary_key=True, autoincrement=True)
    email:         Mapped[str]          = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str]          = mapped_column(String(255), nullable=False)
    platform_role: Mapped[PlatformRole] = mapped_column(
        Enum(PlatformRole, name="platform_role_enum"), default=PlatformRole.support_agent, nullable=False
    )
    full_name:     Mapped[str]          = mapped_column(String(255), default="")
    is_active:     Mapped[bool]         = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:    Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlatformRefreshToken(Base):
    """Refresh tokens for platform_users (separate from employee refresh tokens)."""
    __tablename__ = "platform_refresh_tokens"

    id:             Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_user_id: Mapped[int]         = mapped_column(
        ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash:     Mapped[str]           = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at:     Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at:     Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:     Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())


# ===========================================================================
# TENANT LAYER — every table below is scoped to a tenant
# ===========================================================================

class Department(Base):
    __tablename__ = "departments"

    id:        Mapped[int]          = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int]          = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name:      Mapped[str]          = mapped_column(String(120), nullable=False)
    code:      Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool]         = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime]    = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_dept_tenant_name"),)

    employees: Mapped[list["Employee"]] = relationship(back_populates="department")
    tenant:    Mapped["Tenant"]         = relationship(back_populates="departments")


class Employee(Base):
    __tablename__ = "employees"

    id:            Mapped[int]          = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id:     Mapped[int]          = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    first:         Mapped[str]          = mapped_column(String(80), nullable=False)
    last:          Mapped[str]          = mapped_column(String(80), nullable=False)
    initials:      Mapped[str]          = mapped_column(String(8), nullable=False)
    email:         Mapped[str]          = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone:         Mapped[str]          = mapped_column(String(64), default="")
    role:          Mapped[Role]         = mapped_column(Enum(Role, name="role_enum"), nullable=False)
    title:         Mapped[str]          = mapped_column(String(160), default="")
    salary:        Mapped[float]        = mapped_column(Float, nullable=False)
    status:        Mapped[str]          = mapped_column(String(32), default="active")
    start:         Mapped[date]         = mapped_column(Date, nullable=False)
    manager_id:    Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    department_id: Mapped[int]          = mapped_column(ForeignKey("departments.id"), nullable=False, index=True)

    dob:             Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gender:          Mapped[str]            = mapped_column(String(32), default="Other")
    nationality:     Mapped[str]            = mapped_column(String(80), default="—")
    marital:         Mapped[str]            = mapped_column(String(32), default="Single")
    address:         Mapped[str]            = mapped_column(String(512), default="Remote")
    emergency:       Mapped[str]            = mapped_column(String(256), default="—")
    rating:          Mapped[float]          = mapped_column(Float, default=0)
    goals_completed: Mapped[str]            = mapped_column(String(64), default="0 / 10")
    peer_reviews:    Mapped[int]            = mapped_column(Integer, default=0)
    attendance:      Mapped[dict[str,Any]]  = mapped_column(JSON, nullable=False, default=dict)
    leave_balance:   Mapped[dict[str,str]]  = mapped_column(JSON, nullable=False, default=dict)

    department: Mapped["Department"] = relationship(back_populates="employees")
    tenant:     Mapped["Tenant"]     = relationship(back_populates="employees")


class EmployeeCredential(Base):
    __tablename__ = "employee_credentials"

    employee_id:   Mapped[int]      = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True)
    password_hash: Mapped[str]      = mapped_column(String(255), nullable=False)
    updated_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id:          Mapped[int]         = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id:   Mapped[int]         = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[int]         = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    type:        Mapped[str]         = mapped_column(String(120), nullable=False)
    start_date:  Mapped[date]        = mapped_column(Date, nullable=False)
    end_date:    Mapped[date]        = mapped_column(Date, nullable=False)
    reason:      Mapped[str]         = mapped_column(Text, default="")
    status:      Mapped[LeaveStatus] = mapped_column(Enum(LeaveStatus, name="leave_status_enum"), default=LeaveStatus.pending)


class Task(Base):
    __tablename__ = "tasks"

    id:          Mapped[int]         = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id:   Mapped[int]         = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    title:       Mapped[str]         = mapped_column(String(512), nullable=False)
    assignee_id: Mapped[int]         = mapped_column(ForeignKey("employees.id"), nullable=False)
    due:         Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status:      Mapped[TaskStatus]  = mapped_column(Enum(TaskStatus, name="task_status_enum"), default=TaskStatus.todo)
    priority:    Mapped[Optional[str]] = mapped_column(String(32), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    id:         Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id:  Mapped[int]           = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    target_id:  Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    type:       Mapped[str]           = mapped_column(String(64), nullable=False)
    dot:        Mapped[str]           = mapped_column(String(32), nullable=False)
    title:      Mapped[str]           = mapped_column(String(255), nullable=False)
    text:       Mapped[str]           = mapped_column(Text, nullable=False)
    read:       Mapped[bool]          = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id:  Mapped[int]      = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id:  Mapped[int]      = mapped_column(ForeignKey("employees.id"), nullable=False)
    body:       Mapped[str]      = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int]           = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash:  Mapped[str]           = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at:  Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int]           = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash:  Mapped[str]           = mapped_column(String(64), unique=True, nullable=False)
    purpose:     Mapped[str]           = mapped_column(String(32), nullable=False, default="reset")
    expires_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    used_at:     Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id:               Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id:        Mapped[Optional[int]] = mapped_column(ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_employee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # For platform-level actions the actor is a platform_user
    actor_platform_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("platform_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action:      Mapped[str]           = mapped_column(String(120), nullable=False, index=True)
    entity_type: Mapped[str]           = mapped_column(String(64), nullable=False, index=True)
    entity_id:   Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    payload:     Mapped[Optional[dict[str,Any]]] = mapped_column(JSON, nullable=True)
    ip:          Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())


class DepartmentFeatureFlag(Base):
    __tablename__ = "department_feature_flags"

    id:            Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id:     Mapped[int]           = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id: Mapped[int]           = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    flag_key:      Mapped[str]           = mapped_column(String(64), nullable=False)
    flag_value:    Mapped[Optional[dict[str,Any]]] = mapped_column(JSON, nullable=True)


class LeavePolicy(Base):
    __tablename__ = "leave_policies"

    id:            Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id:     Mapped[int]           = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name:          Mapped[str]           = mapped_column(String(160), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    rules:         Mapped[dict[str,Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at:    Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())


class LeaveAccrualLedger(Base):
    __tablename__ = "leave_accrual_ledger"

    id:            Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id:     Mapped[int]           = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id:   Mapped[int]           = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_type:    Mapped[str]           = mapped_column(String(64), nullable=False)
    hours_delta:   Mapped[float]         = mapped_column(Float, nullable=False)
    balance_after: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    note:          Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at:    Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())


class BlackoutDate(Base):
    __tablename__ = "blackout_dates"

    id:            Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id:     Mapped[int]           = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date:    Mapped[date]          = mapped_column(Date, nullable=False)
    end_date:      Mapped[date]          = mapped_column(Date, nullable=False)
    label:         Mapped[str]           = mapped_column(String(255), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)


class EmployeeDocument(Base):
    __tablename__ = "employee_documents"

    id:              Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id:       Mapped[int]           = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id:     Mapped[int]           = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    label:           Mapped[str]           = mapped_column(String(160), nullable=False)
    storage_key:     Mapped[str]           = mapped_column(String(512), nullable=False)
    mime_type:       Mapped[str]           = mapped_column(String(128), nullable=False)
    size_bytes:      Mapped[int]           = mapped_column(Integer, nullable=False)
    scan_status:     Mapped[str]           = mapped_column(String(32), nullable=False, default="pending")
    retention_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:      Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())