"""security hardening and query indexes

Revision ID: 4f9a1f0c9e21
Revises: b8a78c4249f5
Create Date: 2026-04-28 12:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.crypto import ENVELOPE_PREFIX, encrypt_secret

# revision identifiers, used by Alembic.
revision: str = "4f9a1f0c9e21"
down_revision: str | Sequence[str] | None = "b8a78c4249f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("token_version", sa.Integer(), nullable=False, server_default="1")
        )

    with op.batch_alter_table("channels") as batch_op:
        batch_op.alter_column(
            "secret",
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=True,
        )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, secret FROM channels WHERE secret IS NOT NULL")
    ).mappings()
    for row in rows:
        secret = row["secret"]
        if secret and not str(secret).startswith(ENVELOPE_PREFIX):
            bind.execute(
                sa.text("UPDATE channels SET secret = :secret WHERE id = :id"),
                {"id": row["id"], "secret": encrypt_secret(str(secret))},
            )

    op.execute(sa.text("UPDATE users SET token_version = 1 WHERE token_version IS NULL"))

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("token_version", server_default=None)

    op.create_index("ix_messages_created_at", "messages", ["created_at"], unique=False)
    op.create_index(
        "ix_messages_user_id_created_at",
        "messages",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_deliveries_created_at", "deliveries", ["created_at"], unique=False)
    op.create_index(
        "ix_deliveries_status_next_retry_at",
        "deliveries",
        ["status", "next_retry_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_deliveries_status_next_retry_at", table_name="deliveries")
    op.drop_index("ix_deliveries_created_at", table_name="deliveries")
    op.drop_index("ix_messages_user_id_created_at", table_name="messages")
    op.drop_index("ix_messages_created_at", table_name="messages")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("token_version")

    # Encrypted secrets may exceed the legacy varchar length; keep the safer text type on downgrade.
