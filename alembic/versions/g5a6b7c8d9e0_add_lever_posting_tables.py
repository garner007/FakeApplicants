"""add lever posting tables

Revision ID: g5a6b7c8d9e0
Revises: f4a5b6c7d8e9
Create Date: 2026-01-09 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "g5a6b7c8d9e0"
down_revision: str | Sequence[str] | None = "f4a5b6c7d8e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create lever_postings and applicant_postings tables."""
    # Create lever_postings table
    op.create_table(
        "lever_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lever_posting_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("team", sa.String(255), nullable=True),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("commitment", sa.String(100), nullable=True),
        sa.Column("state", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("lever_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lever_posting_id"),
    )
    op.create_index(
        "ix_lever_postings_lever_posting_id",
        "lever_postings",
        ["lever_posting_id"],
        unique=True,
    )

    # Create applicant_postings junction table
    op.create_table(
        "applicant_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applicant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("posting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lever_opportunity_id", sa.String(255), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stage", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["applicant_id"],
            ["applicants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["posting_id"],
            ["lever_postings.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("applicant_id", "posting_id", name="uq_applicant_posting"),
        sa.UniqueConstraint("lever_opportunity_id", name="uq_lever_opportunity_id"),
    )
    op.create_index(
        "ix_applicant_postings_applicant_id",
        "applicant_postings",
        ["applicant_id"],
    )
    op.create_index(
        "ix_applicant_postings_posting_id",
        "applicant_postings",
        ["posting_id"],
    )
    op.create_index(
        "ix_applicant_postings_lever_opportunity_id",
        "applicant_postings",
        ["lever_opportunity_id"],
    )


def downgrade() -> None:
    """Drop lever_postings and applicant_postings tables."""
    op.drop_table("applicant_postings")
    op.drop_table("lever_postings")
