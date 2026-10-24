"""Additive IELTS 30-week course and per-learner vocabulary state."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7d0a1c2e4f6"
down_revision: str | Sequence[str] | None = "a6c42e91d3f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "course_weeks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("topic", sa.String(length=300), nullable=False),
        sa.Column("grammar", sa.Text(), nullable=False, server_default=""),
        sa.Column("listening", sa.Text(), nullable=False, server_default=""),
        sa.Column("reading_writing", sa.Text(), nullable=False, server_default=""),
        sa.Column("speaking_outcome", sa.Text(), nullable=False, server_default=""),
        sa.UniqueConstraint("week_number", name="uq_course_weeks_week_number"),
    )
    op.create_index("ix_course_weeks_week_number", "course_weeks", ["week_number"])
    op.create_table(
        "course_day_vocabulary",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("vocabulary_id", sa.Integer(), nullable=False),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("owner_id", "day_number", "vocabulary_id", name="uq_course_day_vocab"),
    )
    op.create_index("ix_course_day_vocabulary_owner_id", "course_day_vocabulary", ["owner_id"])
    op.create_index("ix_course_day_vocabulary_day_number", "course_day_vocabulary", ["day_number"])
    op.create_index(
        "ix_course_day_vocabulary_vocabulary_id", "course_day_vocabulary", ["vocabulary_id"]
    )
    for column, kind, nullable, default in (
        ("source_key", sa.String(80), True, None),
        ("course_week", sa.Integer(), True, None),
        ("pronunciation_hint", sa.String(300), False, ""),
        ("collocation", sa.String(300), False, ""),
        ("collocation_translation", sa.String(500), False, ""),
        ("collocation_transcription", sa.String(300), False, ""),
        ("collocation_pronunciation_hint", sa.String(300), False, ""),
    ):
        options = {"nullable": nullable}
        if default is not None:
            options["server_default"] = default
        op.add_column("vocabulary", sa.Column(column, kind, **options))
    op.create_index("ix_vocabulary_source_key", "vocabulary", ["source_key"], unique=True)
    op.create_index("ix_vocabulary_course_week", "vocabulary", ["course_week"])
    op.create_table(
        "vocabulary_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("vocabulary_id", sa.Integer(), nullable=False),
        sa.Column("next_review", sa.Date(), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mastery", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint("owner_id", "vocabulary_id", name="uq_vocab_progress_owner_word"),
    )
    op.create_index("ix_vocabulary_progress_owner_id", "vocabulary_progress", ["owner_id"])
    op.create_index(
        "ix_vocabulary_progress_vocabulary_id", "vocabulary_progress", ["vocabulary_id"]
    )
    op.create_index("ix_vocabulary_progress_next_review", "vocabulary_progress", ["next_review"])
    op.execute(
        sa.text(
            "INSERT INTO vocabulary_progress "
            "(owner_id, vocabulary_id, next_review, interval_days, correct_count, error_count, mastery) "
            "SELECT owner_id, id, next_review, interval_days, correct_count, error_count, mastery "
            "FROM vocabulary WHERE owner_id IS NOT NULL"
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO vocabulary_progress "
            "(owner_id, vocabulary_id, next_review, interval_days, correct_count, error_count, mastery) "
            "SELECT -1, id, CURRENT_DATE, 0, 0, 0, 0 FROM vocabulary WHERE owner_id IS NULL"
        )
    )
    op.add_column(
        "ai_usage",
        sa.Column("provider", sa.String(length=20), nullable=False, server_default="openai"),
    )
    op.create_index("ix_ai_usage_provider", "ai_usage", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_course_day_vocabulary_vocabulary_id", table_name="course_day_vocabulary")
    op.drop_index("ix_course_day_vocabulary_day_number", table_name="course_day_vocabulary")
    op.drop_index("ix_course_day_vocabulary_owner_id", table_name="course_day_vocabulary")
    op.drop_table("course_day_vocabulary")
    op.drop_index("ix_ai_usage_provider", table_name="ai_usage")
    op.drop_column("ai_usage", "provider")
    op.drop_index("ix_vocabulary_progress_next_review", table_name="vocabulary_progress")
    op.drop_index("ix_vocabulary_progress_vocabulary_id", table_name="vocabulary_progress")
    op.drop_index("ix_vocabulary_progress_owner_id", table_name="vocabulary_progress")
    op.drop_table("vocabulary_progress")
    op.drop_index("ix_vocabulary_course_week", table_name="vocabulary")
    op.drop_index("ix_vocabulary_source_key", table_name="vocabulary")
    for column in (
        "collocation_pronunciation_hint",
        "collocation_transcription",
        "collocation_translation",
        "collocation",
        "pronunciation_hint",
        "course_week",
        "source_key",
    ):
        op.drop_column("vocabulary", column)
    op.drop_index("ix_course_weeks_week_number", table_name="course_weeks")
    op.drop_table("course_weeks")
