"""Track active daily Telegram delivery claims.

Revision ID: c518bfe0d7a2
Revises: e84b970ac213
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c518bfe0d7a2"
down_revision: str | Sequence[str] | None = "e84b970ac213"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("daily_deliveries", sa.Column("claimed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("daily_deliveries", "claimed_at")
