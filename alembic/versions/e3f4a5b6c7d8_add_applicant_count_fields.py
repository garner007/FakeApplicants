"""add applicant count fields for mass applicant detection

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-01-09 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: str | Sequence[str] | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add count fields for mass applicant detection.

    These fields track:
    - opportunity_count: Number of jobs the applicant applied to
    - email_count: Number of email addresses provided
    - phone_count: Number of phone numbers provided

    Default value of 1 for existing records is reasonable since
    each applicant has at least one opportunity and contact info.
    """
    op.add_column(
        "applicants",
        sa.Column("opportunity_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "applicants",
        sa.Column("email_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "applicants",
        sa.Column("phone_count", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    """Remove the count fields."""
    op.drop_column("applicants", "phone_count")
    op.drop_column("applicants", "email_count")
    op.drop_column("applicants", "opportunity_count")
