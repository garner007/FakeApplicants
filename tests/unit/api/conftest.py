"""Shared fixtures for API route tests."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from applicant_validator.database import User, UserRole


@pytest.fixture
def mock_user() -> User:
    """Create a mock regular user."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "user@example.com"
    user.name = "Test User"
    user.first_name = "Test"
    user.last_name = "User"
    user.role = UserRole.USER.value
    user.is_active = True
    user.is_deleted = False
    user.must_change_password = False
    user.must_change_email = False
    user.last_login_at = datetime.now(UTC)
    user.created_at = datetime.now(UTC)
    user.password_hash = "hashed_password"  # pragma: allowlist secret
    user.created_by_id = None
    user.is_admin = False
    user.is_superadmin = False
    return user


@pytest.fixture
def mock_admin_user() -> User:
    """Create a mock admin user."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "admin@example.com"
    user.name = "Admin User"
    user.first_name = "Admin"
    user.last_name = "User"
    user.role = UserRole.ADMIN.value
    user.is_active = True
    user.is_deleted = False
    user.must_change_password = False
    user.must_change_email = False
    user.last_login_at = datetime.now(UTC)
    user.created_at = datetime.now(UTC)
    user.password_hash = "hashed_password"  # pragma: allowlist secret
    user.created_by_id = None
    user.is_admin = True
    user.is_superadmin = False
    return user


@pytest.fixture
def mock_superadmin_user() -> User:
    """Create a mock superadmin user."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "superadmin@example.com"
    user.name = "Super Admin"
    user.first_name = "Super"
    user.last_name = "Admin"
    user.role = UserRole.SUPERADMIN.value
    user.is_active = True
    user.is_deleted = False
    user.must_change_password = False
    user.must_change_email = False
    user.last_login_at = datetime.now(UTC)
    user.created_at = datetime.now(UTC)
    user.password_hash = "hashed_password"  # pragma: allowlist secret
    user.created_by_id = None
    user.is_admin = True
    user.is_superadmin = True
    return user


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_auth_settings_cache() -> MagicMock:
    """Create a mock auth settings cache."""
    cache = MagicMock()
    cache.jwt_secret = "test_secret_key_for_testing_purposes_only_12345"  # pragma: allowlist secret
    cache.jwt_expiry_hours = 24
    cache.cookie_name = "session"
    cache.cookie_secure = False
    cache.allowed_domain = ""
    cache.min_password_length = 8
    cache.is_loaded = True
    return cache


def create_test_app_with_auth(
    current_user: User | None = None,
    admin_required: bool = False,
) -> FastAPI:
    """Create a test FastAPI app with mocked authentication.

    Args:
        current_user: User to return for authentication (None for unauthenticated).
        admin_required: Whether admin privileges are required.

    Returns:
        FastAPI app with mocked auth dependencies.
    """
    from fastapi import FastAPI

    from applicant_validator.api.routes.admin import router as admin_router
    from applicant_validator.api.routes.applicants import router as applicants_router
    from applicant_validator.api.routes.auth import router as auth_router
    from applicant_validator.api.routes.revalidate import router as revalidate_router
    from applicant_validator.api.routes.rules import router as rules_router
    from applicant_validator.api.routes.settings import router as settings_router
    from applicant_validator.api.routes.sync import router as sync_router
    from applicant_validator.api.routes.users import router as users_router
    from applicant_validator.api.routes.validation_data import router as validation_data_router

    app = FastAPI()
    app.include_router(admin_router, prefix="/api")
    app.include_router(applicants_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(revalidate_router, prefix="/api")
    app.include_router(rules_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")
    app.include_router(sync_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(validation_data_router, prefix="/api")

    return app


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing routes without auth."""
    from applicant_validator.api.routes.rules import router as rules_router
    from applicant_validator.api.routes.sync import router as sync_router

    app = FastAPI()
    app.include_router(rules_router, prefix="/api")
    app.include_router(sync_router, prefix="/api")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
