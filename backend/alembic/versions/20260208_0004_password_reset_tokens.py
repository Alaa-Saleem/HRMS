"""password reset / invite tokens

Revision ID: 20260208_0004
Revises: 20260207_0003

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260208_0004"
down_revision: Union[str, Sequence[str], None] = "20260207_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False, server_default="reset"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_token_hash"),
    )
    op.create_index("ix_password_reset_tokens_employee_id", "password_reset_tokens", ["employee_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_employee_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
