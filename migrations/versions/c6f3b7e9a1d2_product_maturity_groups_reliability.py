"""product maturity groups reliability

Revision ID: c6f3b7e9a1d2
Revises: 8b7a3c1d2e44
Create Date: 2026-04-28 14:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6f3b7e9a1d2"
down_revision: str | Sequence[str] | None = "8b7a3c1d2e44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_groups",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_groups_name", "user_groups", ["name"], unique=True)

    op.create_table(
        "user_group_members",
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["group_id"], ["user_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "user_id"),
    )
    op.create_index(
        "ix_user_group_members_user_id",
        "user_group_members",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "user_group_channel_permissions",
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("channel_id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["user_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "channel_id"),
    )
    op.create_index(
        "ix_user_group_channel_permissions_channel_id",
        "user_group_channel_permissions",
        ["channel_id"],
        unique=False,
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_audit_logs_target_id", "audit_logs", ["target_id"], unique=False)
    op.create_index("ix_audit_logs_target_type", "audit_logs", ["target_type"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)

    with op.batch_alter_table("messages") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("idempotency_hash", sa.String(length=64), nullable=True))
        batch_op.create_unique_constraint(
            "uq_messages_push_key_idempotency_key",
            ["push_key_id", "idempotency_key"],
        )
        batch_op.create_index("ix_messages_idempotency_key", ["idempotency_key"], unique=False)

    with op.batch_alter_table("deliveries") as batch_op:
        batch_op.add_column(
            sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index(
            "ix_deliveries_status_processing_started_at",
            ["status", "processing_started_at"],
            unique=False,
        )
        batch_op.create_index(
            "ix_deliveries_dead_lettered_at",
            ["dead_lettered_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("deliveries") as batch_op:
        batch_op.drop_index("ix_deliveries_dead_lettered_at")
        batch_op.drop_index("ix_deliveries_status_processing_started_at")
        batch_op.drop_column("dead_lettered_at")
        batch_op.drop_column("processing_started_at")

    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_index("ix_messages_idempotency_key")
        batch_op.drop_constraint("uq_messages_push_key_idempotency_key", type_="unique")
        batch_op.drop_column("idempotency_hash")
        batch_op.drop_column("idempotency_key")

    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_target_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_target_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(
        "ix_user_group_channel_permissions_channel_id",
        table_name="user_group_channel_permissions",
    )
    op.drop_table("user_group_channel_permissions")

    op.drop_index("ix_user_group_members_user_id", table_name="user_group_members")
    op.drop_table("user_group_members")

    op.drop_index("ix_user_groups_name", table_name="user_groups")
    op.drop_table("user_groups")
