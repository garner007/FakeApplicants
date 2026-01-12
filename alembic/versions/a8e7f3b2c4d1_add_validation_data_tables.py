"""add validation data tables

Revision ID: a8e7f3b2c4d1
Revises: 46f4a85f5c34
Create Date: 2026-01-07 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a8e7f3b2c4d1"
down_revision: str | Sequence[str] | None = "46f4a85f5c34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - add validation data tables."""
    # Create disposable_email_domains table
    op.create_table(
        "disposable_email_domains",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("domain", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("source", sa.String(50), nullable=False, default="external_list"),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
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
    op.create_index(
        "ix_disposable_domains_active", "disposable_email_domains", ["domain", "is_active"]
    )

    # Create voip_carriers table
    op.create_table(
        "voip_carriers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("match_type", sa.String(50), nullable=False, default="substring"),
        sa.Column("source", sa.String(50), nullable=False, default="custom"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("confidence", sa.String(50), nullable=False, default="high"),
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

    # Create voip_area_codes table
    op.create_table(
        "voip_area_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("area_code", sa.String(10), nullable=False, unique=True, index=True),
        sa.Column("country_code", sa.String(5), nullable=False, default="1"),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("source", sa.String(50), nullable=False, default="custom"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
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

    # Create validation_data_syncs table
    op.create_table(
        "validation_data_syncs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("data_type", sa.String(100), nullable=False, index=True),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("records_added", sa.Integer(), nullable=False, default=0),
        sa.Column("records_updated", sa.Integer(), nullable=False, default=0),
        sa.Column("records_total", sa.Integer(), nullable=False, default=0),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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


def downgrade() -> None:
    """Downgrade schema - remove validation data tables."""
    op.drop_table("validation_data_syncs")
    op.drop_index("ix_disposable_domains_active", table_name="disposable_email_domains")
    op.drop_table("voip_area_codes")
    op.drop_table("voip_carriers")
    op.drop_table("disposable_email_domains")
