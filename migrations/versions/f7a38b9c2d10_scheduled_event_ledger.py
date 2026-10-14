"""scheduled event idempotency ledger

Revision ID: scheduled_event_v3
Revises: course_vocabulary_day_v3
Create Date: 2026-10-14 19:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "scheduled_event_v3"
down_revision: str | Sequence[str] | None = "course_vocabulary_day_v3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduled_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_key", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key", name="uq_scheduled_event_key"),
    )
    op.create_index(
        op.f("ix_scheduled_events_event_key"), "scheduled_events", ["event_key"], unique=False
    )
    op.create_index(
        op.f("ix_scheduled_events_event_type"), "scheduled_events", ["event_type"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_scheduled_events_event_type"), table_name="scheduled_events")
    op.drop_index(op.f("ix_scheduled_events_event_key"), table_name="scheduled_events")
    op.drop_table("scheduled_events")
