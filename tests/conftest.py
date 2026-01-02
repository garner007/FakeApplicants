"""Shared pytest fixtures for all tests."""

import os
from collections.abc import Generator

import pytest


@pytest.fixture
def mock_env_vars() -> Generator[dict[str, str], None, None]:
    """Provide mock environment variables for testing."""
    env_vars = {
        "LEVER_API_KEY": "test_lever_api_key_12345",
        "LEVER_ENVIRONMENT": "sandbox",
        "LINKEDIN_CLIENT_ID": "test_linkedin_client_id",
        "LINKEDIN_CLIENT_SECRET": "test_linkedin_client_secret",
        "LINKEDIN_REDIRECT_URI": "http://localhost:8000/auth/linkedin/callback",
        "LINKEDIN_ENVIRONMENT": "development",
        "APP_ENV": "development",
        "LOG_LEVEL": "DEBUG",
        "API_HOST": "0.0.0.0",
        "API_PORT": "8000",
        "ENABLE_LINKEDIN_INTEGRATION": "true",
        "ENABLE_ADVANCED_VALIDATORS": "false",
        "DEBUG_MODE": "true",
        "LEVER_RATE_LIMIT": "10",
        "LINKEDIN_RATE_LIMIT": "5",
    }

    # Store original values
    original_env: dict[str, str | None] = {}
    for key in env_vars:
        original_env[key] = os.environ.get(key)

    # Set test values
    os.environ.update(env_vars)

    yield env_vars

    # Restore original values
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def minimal_env_vars() -> Generator[dict[str, str], None, None]:
    """Provide minimal required environment variables."""
    env_vars = {
        "LEVER_API_KEY": "test_lever_api_key",
        "LINKEDIN_CLIENT_ID": "test_client_id",
        "LINKEDIN_CLIENT_SECRET": "test_client_secret",
    }

    # Store original values
    original_env: dict[str, str | None] = {}
    for key in env_vars:
        original_env[key] = os.environ.get(key)

    # Set test values
    os.environ.update(env_vars)

    yield env_vars

    # Restore original values
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
