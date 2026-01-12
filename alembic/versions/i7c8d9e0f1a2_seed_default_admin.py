"""Seed default admin user with one-time credentials.

Revision ID: i7c8d9e0f1a2
Revises: h6b7c8d9e0f1
Create Date: 2026-01-10

This migration:
1. Adds must_change_email column to users table
2. Seeds a default superadmin user with credentials:
   - Email: admin@localhost
   - Password: changeme123!

IMPORTANT: Both email AND password must be changed on first login.
"""

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i7c8d9e0f1a2"
down_revision: str | None = "h6b7c8d9e0f1"
branch_labels: str | None = None
depends_on: str | None = None

# Default admin credentials - MUST BE CHANGED ON FIRST LOGIN
DEFAULT_ADMIN_EMAIL = "admin@localhost"
DEFAULT_ADMIN_PASSWORD = "changeme123!"
DEFAULT_ADMIN_NAME = "Administrator"


def upgrade() -> None:
    """Add must_change_email column and seed default admin user."""
    # Add must_change_email column
    op.add_column(
        "users",
        sa.Column("must_change_email", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Check if any users already exist
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT COUNT(*) FROM users"))
    user_count = result.scalar()

    if user_count > 0:
        print(f"Users already exist ({user_count}), skipping default admin seeding.")
        return

    # Hash the password using passlib/bcrypt
    try:
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        password_hash = pwd_context.hash(DEFAULT_ADMIN_PASSWORD)

        # Insert default superadmin user with both change flags set
        op.execute(
            sa.text(
                """
                INSERT INTO users (
                    id, email, password_hash, name, role,
                    is_active, must_change_password, must_change_email,
                    created_at, updated_at, is_deleted
                )
                VALUES (
                    CAST(:id AS UUID), :email, :password_hash, :name, 'superadmin',
                    true, true, true,
                    :now, :now, false
                )
                """
            ).bindparams(
                id=str(uuid.uuid4()),
                email=DEFAULT_ADMIN_EMAIL,
                password_hash=password_hash,
                name=DEFAULT_ADMIN_NAME,
                now=datetime.now(UTC),
            )
        )
        print("")
        print("=" * 60)
        print("DEFAULT ADMIN USER CREATED")
        print("=" * 60)
        print(f"  Email:    {DEFAULT_ADMIN_EMAIL}")
        print(f"  Password: {DEFAULT_ADMIN_PASSWORD}")
        print("")
        print("  *** BOTH EMAIL AND PASSWORD MUST BE CHANGED ON FIRST LOGIN ***")
        print("=" * 60)
        print("")

    except ImportError:
        print("ERROR: passlib not installed, cannot seed admin user")
        print("Run: pip install passlib[bcrypt]")
        raise
    except Exception as e:
        print(f"ERROR: Failed to seed admin user: {e}")
        raise


def downgrade() -> None:
    """Remove the column and default admin user."""
    # Remove default admin user
    op.execute(
        sa.text("DELETE FROM users WHERE email = :email").bindparams(email=DEFAULT_ADMIN_EMAIL)
    )
    # Remove the column
    op.drop_column("users", "must_change_email")
