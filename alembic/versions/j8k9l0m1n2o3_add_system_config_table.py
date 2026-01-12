"""Add system_config table for auth and other settings.

Revision ID: j8k9l0m1n2o3
Revises: i7c8d9e0f1a2
Create Date: 2026-01-11

This migration adds the system_config table which stores:
- Auth settings (JWT secret, expiry, cookie config)
- Other configurable system settings
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "j8k9l0m1n2o3"
down_revision: str | None = "i7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create system_config table."""
    op.create_table(
        "system_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("value_type", sa.String(50), nullable=False, server_default="string"),
        sa.Column("category", sa.String(100), nullable=False, server_default="general", index=True),
        sa.Column("is_editable", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    """Drop system_config table."""
    op.drop_table("system_config")
