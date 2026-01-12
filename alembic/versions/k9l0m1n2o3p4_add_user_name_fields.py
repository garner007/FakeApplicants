"""Add first_name and last_name fields to users table.

Revision ID: k9l0m1n2o3p4
Revises: j8k9l0m1n2o3
Create Date: 2026-01-11

This migration adds optional first_name and last_name columns
to the users table for better user management.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k9l0m1n2o3p4"
down_revision: str | None = "j8k9l0m1n2o3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add first_name and last_name columns to users table."""
    op.add_column(
        "users",
        sa.Column("first_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_name", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    """Remove first_name and last_name columns from users table."""
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
