"""Seed global default leave policy when table empty.

Revision ID: 20260209_0005
Revises: 20260208_0004

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260209_0005"
down_revision: Union[str, Sequence[str], None] = "20260208_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    n = conn.execute(sa.text("SELECT COUNT(*) FROM leave_policies")).scalar()
    if n is not None and int(n) > 0:
        return
    op.execute(
        sa.text(
            """
            INSERT INTO leave_policies (name, department_id, rules)
            VALUES (
              :name,
              NULL,
              CAST(:rules AS JSON)
            )
            """
        ).bindparams(
            name="Default (global)",
            rules='{"allowed_leave_types":["Annual","Paid Leave","Sick Leave","Personal Leave"],"max_consecutive_calendar_days":30,"enforce_ledger":false,"hours_per_day":8}',
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM leave_policies WHERE name = 'Default (global)' AND department_id IS NULL"))
