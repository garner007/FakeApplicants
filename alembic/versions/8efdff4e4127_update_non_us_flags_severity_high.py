"""update_non_us_flags_severity_high

Revision ID: 8efdff4e4127
Revises: dfd7398a2b40
Create Date: 2026-01-08 16:54:42.658062

Updates non-US phone and location flags from MEDIUM to HIGH severity.
This reflects the US-only hiring policy where non-US applicants are high risk.
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8efdff4e4127"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "dfd7398a2b40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Update non_us_phone and non_us_location flags to HIGH severity."""
    # Update flag_types default_severity
    op.execute(
        """
        UPDATE flag_types
        SET default_severity = 'high'
        WHERE code IN ('non_us_phone', 'non_us_location')
        AND default_severity = 'medium'
        """
    )

    # Update existing flags via join with flag_types
    op.execute(
        """
        UPDATE flags
        SET severity = 'high'
        FROM flag_types
        WHERE flags.flag_type_id = flag_types.id
        AND flag_types.code IN ('non_us_phone', 'non_us_location')
        AND flags.severity = 'medium'
        """
    )

    # Update validation_results table severity
    op.execute(
        """
        UPDATE validation_results
        SET severity = 'high'
        WHERE rule_name IN ('non_us_phone', 'non_us_location')
        AND severity = 'medium'
        """
    )


def downgrade() -> None:
    """Revert non_us_phone and non_us_location flags to MEDIUM severity."""
    # Revert flag_types default_severity
    op.execute(
        """
        UPDATE flag_types
        SET default_severity = 'medium'
        WHERE code IN ('non_us_phone', 'non_us_location')
        AND default_severity = 'high'
        """
    )

    # Revert existing flags via join with flag_types
    op.execute(
        """
        UPDATE flags
        SET severity = 'medium'
        FROM flag_types
        WHERE flags.flag_type_id = flag_types.id
        AND flag_types.code IN ('non_us_phone', 'non_us_location')
        AND flags.severity = 'high'
        """
    )

    # Revert validation_results table severity
    op.execute(
        """
        UPDATE validation_results
        SET severity = 'medium'
        WHERE rule_name IN ('non_us_phone', 'non_us_location')
        AND severity = 'high'
        """
    )
