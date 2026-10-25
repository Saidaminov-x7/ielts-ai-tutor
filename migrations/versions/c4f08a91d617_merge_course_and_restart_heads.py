"""Merge the course and owner scoped restart migration branches.

Revision ID: c4f08a91d617
Revises: a7e618f4b302, b7d0a1c2e4f6
"""

from collections.abc import Sequence

revision: str = "c4f08a91d617"
down_revision: str | Sequence[str] | None = ("a7e618f4b302", "b7d0a1c2e4f6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
