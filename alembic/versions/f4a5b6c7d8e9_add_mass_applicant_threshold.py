"""add mass applicant threshold to lever config

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-01-09 16:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a5b6c7d8e9"
down_revision: str | Sequence[str] | None = "e3f4a5b6c7d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add default mass_applicant_threshold to Lever integration config_json.

    Sets the default threshold to 5 - applicants with 5 or more opportunities
    will be flagged as mass applicants.

    This updates the config_json field to include the threshold setting
    while preserving any existing configuration (like environment).
    """
    # Update Lever config_json to include mass_applicant_threshold
    # Use COALESCE to handle NULL config_json, and jsonb operations to merge
    op.execute(
        """
        UPDATE integration_settings
        SET config_json = COALESCE(config_json::jsonb, '{}'::jsonb)
            || '{"mass_applicant_threshold": 5}'::jsonb
        WHERE provider = 'lever'
    """
    )


def downgrade() -> None:
    """Remove mass_applicant_threshold from Lever integration config_json."""
    op.execute(
        """
        UPDATE integration_settings
        SET config_json = (config_json::jsonb - 'mass_applicant_threshold')::text
        WHERE provider = 'lever'
    """
    )
