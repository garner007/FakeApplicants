"""increase api_key column size for JWT tokens

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-01-09 13:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision: str | Sequence[str] | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Change api_key and api_secret columns from VARCHAR(500) to TEXT."""
    op.alter_column(
        "integration_settings",
        "api_key",
        existing_type=sa.VARCHAR(500),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "integration_settings",
        "api_secret",
        existing_type=sa.VARCHAR(500),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert to VARCHAR(500) - may truncate data!"""
    op.alter_column(
        "integration_settings",
        "api_key",
        existing_type=sa.Text(),
        type_=sa.VARCHAR(500),
        existing_nullable=True,
    )
    op.alter_column(
        "integration_settings",
        "api_secret",
        existing_type=sa.Text(),
        type_=sa.VARCHAR(500),
        existing_nullable=True,
    )
