"""initial schema

Revision ID: 20260203_0001
Revises:
Create Date: 2026-02-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260203_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE role_enum AS ENUM ('admin','manager','employee')")
    op.execute("CREATE TYPE leave_status_enum AS ENUM ('pending','approved','rejected')")
    op.execute("CREATE TYPE task_status_enum AS ENUM ('todo','inprogress','done')")

    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("first", sa.String(length=80), nullable=False),
        sa.Column("last", sa.String(length=80), nullable=False),
        sa.Column("initials", sa.String(length=8), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=False),
        sa.Column("role", postgresql.ENUM("admin", "manager", "employee", name="role_enum", create_type=False), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("salary", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("start", sa.Date(), nullable=False),
        sa.Column("manager_id", sa.Integer(), nullable=True),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("dob", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(length=32), nullable=False),
        sa.Column("nationality", sa.String(length=80), nullable=False),
        sa.Column("marital", sa.String(length=32), nullable=False),
        sa.Column("address", sa.String(length=512), nullable=False),
        sa.Column("emergency", sa.String(length=256), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("goals_completed", sa.String(length=64), nullable=False),
        sa.Column("peer_reviews", sa.Integer(), nullable=False),
        sa.Column("attendance", sa.JSON(), nullable=False),
        sa.Column("leave_balance", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["manager_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_employees_email"), "employees", ["email"], unique=True)
    op.create_index(op.f("ix_employees_manager_id"), "employees", ["manager_id"], unique=False)
    op.create_index(op.f("ix_employees_department_id"), "employees", ["department_id"], unique=False)

    op.create_table(
        "employee_credentials",
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("employee_id"),
    )

    op.create_table(
        "leave_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=120), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "approved", "rejected", name="leave_status_enum", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_leave_requests_employee_id"), "leave_requests", ["employee_id"], unique=False)

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("assignee_id", sa.Integer(), nullable=False),
        sa.Column("due", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("todo", "inprogress", "done", name="task_status_enum", create_type=False),
            nullable=False,
            server_default="todo",
        ),
        sa.Column("priority", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(["assignee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("dot", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["target_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_target_id"), "notifications", ["target_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sender_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("notifications")
    op.drop_table("tasks")
    op.drop_table("leave_requests")
    op.drop_table("employee_credentials")
    op.drop_index(op.f("ix_employees_email"), table_name="employees")
    op.drop_index(op.f("ix_employees_manager_id"), table_name="employees")
    op.drop_index(op.f("ix_employees_department_id"), table_name="employees")
    op.drop_table("employees")
    op.drop_table("departments")
    op.execute("DROP TYPE IF EXISTS task_status_enum")
    op.execute("DROP TYPE IF EXISTS leave_status_enum")
    op.execute("DROP TYPE IF EXISTS role_enum")
