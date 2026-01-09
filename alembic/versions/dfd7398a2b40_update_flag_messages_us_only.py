"""update_flag_messages_us_only

Revision ID: dfd7398a2b40
Revises: ded2f381692a
Create Date: 2026-01-08 15:44:51.484631

Updates flag messages to reflect US-only hiring policy.
Changes "US/Canada" references to just "US".
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dfd7398a2b40"  # pragma: allowlist secret
down_revision: str | Sequence[str] | None = "ded2f381692a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Update flag messages to remove Canada references."""
    # Update flags table messages
    op.execute(
        """
        UPDATE flags
        SET message = REPLACE(message, 'outside US/Canada', 'outside the US')
        WHERE message LIKE '%outside US/Canada%'
        """
    )
    op.execute(
        """
        UPDATE flags
        SET message = REPLACE(message, 'US/Canada', 'US')
        WHERE message LIKE '%US/Canada%'
        """
    )

    # Update validation_results table messages
    op.execute(
        """
        UPDATE validation_results
        SET message = REPLACE(message, 'outside US/Canada', 'outside the US')
        WHERE message LIKE '%outside US/Canada%'
        """
    )
    op.execute(
        """
        UPDATE validation_results
        SET message = REPLACE(message, 'US/Canada', 'US')
        WHERE message LIKE '%US/Canada%'
        """
    )


def downgrade() -> None:
    """Revert flag messages (not strictly reversible, but attempt to restore)."""
    # This is a data migration, exact reversal isn't possible
    # but we can attempt to restore the original format
    op.execute(
        """
        UPDATE flags
        SET message = REPLACE(message, 'outside the US', 'outside US/Canada')
        WHERE message LIKE '%outside the US%'
        AND (message LIKE '%Phone number%' OR message LIKE '%Location%')
        """
    )
    op.execute(
        """
        UPDATE validation_results
        SET message = REPLACE(message, 'outside the US', 'outside US/Canada')
        WHERE message LIKE '%outside the US%'
        AND (message LIKE '%Phone number%' OR message LIKE '%Location%')
        """
    )
