"""add integration settings table

Revision ID: b9f8c4d5e6a2
Revises: a8e7f3b2c4d1
Create Date: 2026-01-07 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b9f8c4d5e6a2"
down_revision: str | Sequence[str] | None = "a8e7f3b2c4d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - add integration_settings table."""
    op.create_table(
        "integration_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("api_key", sa.String(500), nullable=True),
        sa.Column("api_secret", sa.String(500), nullable=True),
        sa.Column("account_id", sa.String(255), nullable=True),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("fraud_score_threshold", sa.Integer(), nullable=True),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_success", sa.Boolean(), nullable=True),
        sa.Column("last_test_message", sa.String(500), nullable=True),
        sa.Column("monthly_usage", sa.Integer(), nullable=False, default=0),
        sa.Column("monthly_limit", sa.Integer(), nullable=True),
        sa.Column("usage_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Seed default integration settings
    op.execute(
        """
        INSERT INTO integration_settings (
            id, provider, display_name, is_enabled,
            fraud_score_threshold, monthly_limit, monthly_usage
        )
        VALUES
            (gen_random_uuid(), 'ipqualityscore', 'IPQualityScore', false, 85, 1000, 0),
            (gen_random_uuid(), 'twilio', 'Twilio', false, null, null, 0)
    """
    )


def downgrade() -> None:
    """Downgrade schema - remove integration_settings table."""
    op.drop_table("integration_settings")
