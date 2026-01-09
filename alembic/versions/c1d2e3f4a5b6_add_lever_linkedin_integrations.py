"""add lever and linkedin integrations

Revision ID: c1d2e3f4a5b6
Revises: 8efdff4e4127
Create Date: 2026-01-08 10:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: str | Sequence[str] | None = "8efdff4e4127"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add Lever and LinkedIn integration settings."""
    # Insert Lever and LinkedIn integrations if they don't exist
    op.execute(
        """
        INSERT INTO integration_settings (id, provider, display_name, is_enabled, monthly_usage)
        SELECT gen_random_uuid(), 'lever', 'Lever', false, 0
        WHERE NOT EXISTS (SELECT 1 FROM integration_settings WHERE provider = 'lever')
    """
    )
    op.execute(
        """
        INSERT INTO integration_settings (id, provider, display_name, is_enabled, monthly_usage)
        SELECT gen_random_uuid(), 'linkedin', 'LinkedIn', false, 0
        WHERE NOT EXISTS (SELECT 1 FROM integration_settings WHERE provider = 'linkedin')
    """
    )


def downgrade() -> None:
    """Remove Lever and LinkedIn integration settings."""
    op.execute("DELETE FROM integration_settings WHERE provider IN ('lever', 'linkedin')")
