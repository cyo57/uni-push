"""make push key rotation timestamp timezone aware

Revision ID: 8b7a3c1d2e44
Revises: 4f9a1f0c9e21
Create Date: 2026-04-28 15:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b7a3c1d2e44"
down_revision: str | Sequence[str] | None = "4f9a1f0c9e21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("push_keys") as batch_op:
        batch_op.alter_column(
            "last_rotated_at",
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("push_keys") as batch_op:
        batch_op.alter_column(
            "last_rotated_at",
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=False,
        )
