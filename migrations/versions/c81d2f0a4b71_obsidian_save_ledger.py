"""Obsidian save idempotency ledger

Revision ID: obsidian_save_v1
Revises: daily_delivery_v2, scheduled_event_v3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "obsidian_save_v1"
down_revision: str | Sequence[str] | None = ("daily_delivery_v2", "scheduled_event_v3")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "obsidian_saves",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("update_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("owner_id", "update_id", name="uq_obsidian_save_update"),
    )
    op.create_index("ix_obsidian_saves_owner_id", "obsidian_saves", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_obsidian_saves_owner_id", table_name="obsidian_saves")
    op.drop_table("obsidian_saves")
