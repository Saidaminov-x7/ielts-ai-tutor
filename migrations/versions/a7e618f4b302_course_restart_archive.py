"""Add per-learner course restart archival.

Revision ID: a7e618f4b302
Revises: d291a4f08c33
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7e618f4b302"
down_revision: str | Sequence[str] | None = "d291a4f08c33"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_settings", sa.Column("course_started_at", sa.DateTime(), nullable=True))
    op.add_column("user_settings", sa.Column("course_schedule_day", sa.Integer(), nullable=True))
    op.create_table(
        "course_reset_archives",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("reset_at", sa.DateTime(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.add_column(
        "course_reset_archives", sa.Column("request_key", sa.String(length=80), nullable=True)
    )
    op.create_index(
        "uq_course_reset_owner_request",
        "course_reset_archives",
        ["owner_id", "request_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_course_reset_archives_owner_id"),
        "course_reset_archives",
        ["owner_id"],
        unique=False,
    )


def downgrade() -> None:
    archive_count = op.get_bind().execute(
        sa.text("SELECT COUNT(*) FROM course_reset_archives")
    ).scalar_one()
    if archive_count:
        raise RuntimeError(
            "Cannot downgrade while course reset archives exist. Export and verify them first."
        )
    op.drop_index("uq_course_reset_owner_request", table_name="course_reset_archives")
    op.drop_column("course_reset_archives", "request_key")
    op.drop_index(op.f("ix_course_reset_archives_owner_id"), table_name="course_reset_archives")
    op.drop_table("course_reset_archives")
    op.drop_column("user_settings", "course_schedule_day")
    op.drop_column("user_settings", "course_started_at")
