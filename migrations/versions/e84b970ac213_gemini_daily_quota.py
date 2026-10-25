"""Shared atomic daily Gemini request quota.

Revision ID: e84b970ac213
Revises: c4f08a91d617
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e84b970ac213"
down_revision: str | Sequence[str] | None = "c4f08a91d617"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gemini_daily_quotas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("request_date", sa.Date(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "owner_id", "request_date", name="uq_gemini_daily_quota_owner_date"
        ),
    )
    op.create_index(op.f("ix_gemini_daily_quotas_owner_id"), "gemini_daily_quotas", ["owner_id"])
    op.create_index(
        op.f("ix_gemini_daily_quotas_request_date"), "gemini_daily_quotas", ["request_date"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_gemini_daily_quotas_request_date"), table_name="gemini_daily_quotas")
    op.drop_index(op.f("ix_gemini_daily_quotas_owner_id"), table_name="gemini_daily_quotas")
    op.drop_table("gemini_daily_quotas")
