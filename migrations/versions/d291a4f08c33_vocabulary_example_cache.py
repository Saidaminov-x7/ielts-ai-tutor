"""Cache validated translated vocabulary examples.

Revision ID: d291a4f08c33
Revises: obsidian_save_v1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d291a4f08c33"
down_revision: str | Sequence[str] | None = "obsidian_save_v1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vocabulary_example_sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vocabulary_id", sa.Integer(), nullable=False),
        sa.Column("examples_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("pending_since", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("vocabulary_id", name="uq_vocabulary_example_sets_vocabulary_id"),
    )
    op.create_index(
        op.f("ix_vocabulary_example_sets_vocabulary_id"),
        "vocabulary_example_sets",
        ["vocabulary_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_vocabulary_example_sets_vocabulary_id"),
        table_name="vocabulary_example_sets",
    )
    op.drop_table("vocabulary_example_sets")
