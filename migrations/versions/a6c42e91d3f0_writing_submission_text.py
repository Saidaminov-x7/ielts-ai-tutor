"""Store submitted text for new Writing evaluations.

Revision ID: a6c42e91d3f0
Revises: obsidian_save_v1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a6c42e91d3f0"
down_revision: str | Sequence[str] | None = "obsidian_save_v1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("writing_attempts", sa.Column("submission_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("writing_attempts", "submission_text")
