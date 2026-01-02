"""Tests for configuration module."""

import os

from applicant_validator.config import Settings


class TestSettings:
    """Tests for the Settings configuration class."""

    def test_settings_loads_from_environment(self, mock_env_vars: dict[str, str]) -> None:
        """Settings should load values from environment variables."""
        settings = Settings()

        assert settings.lever_api_key == "test_lever_api_key_12345"
        assert settings.lever_environment == "sandbox"
        assert settings.linkedin_client_id == "test_linkedin_client_id"
        assert settings.linkedin_client_secret == "test_linkedin_client_secret"
        assert settings.app_env == "development"
        assert settings.log_level == "DEBUG"

    def test_settings_with_minimal_env_vars(self, minimal_env_vars: dict[str, str]) -> None:
        """Settings should work with only required environment variables."""
        settings = Settings()

        # Required fields should be set
        assert settings.lever_api_key == "test_lever_api_key"
        assert settings.linkedin_client_id == "test_client_id"
        assert settings.linkedin_client_secret == "test_client_secret"

        # Optional fields should have defaults
        assert settings.lever_environment == "sandbox"
        assert settings.app_env == "development"
        assert settings.log_level == "INFO"

    def test_settings_with_defaults(self) -> None:
        """Settings should work with default values for API keys."""
        # Clear any existing env vars
        for key in ["LEVER_API_KEY", "LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"]:
            os.environ.pop(key, None)

        # Should not raise - API keys are optional for development
        settings = Settings()
        assert settings.lever_api_key == ""
        assert settings.linkedin_client_id == ""
        assert settings.linkedin_client_secret == ""

    def test_lever_base_url_sandbox(self, mock_env_vars: dict[str, str]) -> None:
        """lever_base_url should return sandbox URL when environment is sandbox."""
        settings = Settings()
        assert settings.lever_base_url == "https://api.sandbox.lever.co/v1"

    def test_lever_base_url_production(self, mock_env_vars: dict[str, str]) -> None:
        """lever_base_url should return production URL when environment is production."""
        os.environ["LEVER_ENVIRONMENT"] = "production"
        settings = Settings()
        assert settings.lever_base_url == "https://api.lever.co/v1"

    def test_feature_flags(self, mock_env_vars: dict[str, str]) -> None:
        """Feature flags should be properly parsed as booleans."""
        settings = Settings()

        assert settings.enable_linkedin_integration is True
        assert settings.enable_advanced_validators is False
        assert settings.debug_mode is True

    def test_rate_limits(self, mock_env_vars: dict[str, str]) -> None:
        """Rate limits should be properly parsed as integers."""
        settings = Settings()

        assert settings.lever_rate_limit == 10
        assert settings.linkedin_rate_limit == 5

    def test_api_configuration(self, mock_env_vars: dict[str, str]) -> None:
        """API host and port should be properly loaded."""
        settings = Settings()

        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000

    def test_linkedin_redirect_uri(self, mock_env_vars: dict[str, str]) -> None:
        """LinkedIn redirect URI should be properly loaded."""
        settings = Settings()
        assert settings.linkedin_redirect_uri == "http://localhost:8000/auth/linkedin/callback"

    def test_is_production_property(self, mock_env_vars: dict[str, str]) -> None:
        """is_production should return True only for production environment."""
        settings = Settings()
        assert settings.is_production is False

        os.environ["APP_ENV"] = "production"
        settings = Settings()
        assert settings.is_production is True

    def test_is_debug_property(self, mock_env_vars: dict[str, str]) -> None:
        """is_debug should return True when debug_mode is enabled and not production."""
        settings = Settings()
        assert settings.is_debug is True

        # Debug should be False in production even if debug_mode is True
        os.environ["APP_ENV"] = "production"
        settings = Settings()
        assert settings.is_debug is False
