"""Configuration management for the Applicant Validator application.

This module uses Pydantic Settings to manage configuration from environment
variables with validation and type coercion.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required environment variables:
        - LEVER_API_KEY: API key for Lever integration
        - LINKEDIN_CLIENT_ID: OAuth client ID for LinkedIn
        - LINKEDIN_CLIENT_SECRET: OAuth client secret for LinkedIn

    All other settings have sensible defaults for development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Lever API Configuration
    lever_api_key: str = Field(default="", description="Lever API key for authentication")
    lever_environment: str = Field(
        default="sandbox", description="Lever environment: sandbox or production"
    )

    # LinkedIn API Configuration
    linkedin_client_id: str = Field(default="", description="LinkedIn OAuth client ID")
    linkedin_client_secret: str = Field(default="", description="LinkedIn OAuth client secret")
    linkedin_redirect_uri: str = Field(
        default="http://localhost:8000/auth/linkedin/callback",
        description="LinkedIn OAuth redirect URI",
    )
    linkedin_environment: str = Field(
        default="development",
        description="LinkedIn environment: development or production",
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://applicant_validator:dev_password_change_me@localhost:5432/applicant_validator",
        description="PostgreSQL connection URL",
    )
    database_pool_size: int = Field(default=5, description="Database connection pool size")
    database_max_overflow: int = Field(
        default=10, description="Max overflow connections beyond pool size"
    )

    # Application Configuration
    app_env: str = Field(
        default="development",
        description="Application environment: development, staging, or production",
    )
    log_level: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR")

    # API Server Configuration
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")

    # Feature Flags
    enable_linkedin_integration: bool = Field(
        default=True, description="Enable LinkedIn API integration"
    )
    enable_advanced_validators: bool = Field(
        default=False, description="Enable advanced validation rules (Phase 2+)"
    )
    debug_mode: bool = Field(default=False, description="Enable debug mode (additional logging)")

    # Rate Limiting
    lever_rate_limit: int = Field(default=10, description="Max requests per second to Lever API")
    linkedin_rate_limit: int = Field(
        default=5, description="Max requests per second to LinkedIn API"
    )

    @property
    def lever_base_url(self) -> str:
        """Get the Lever API base URL based on environment."""
        if self.lever_environment == "sandbox":
            return "https://api.sandbox.lever.co/v1"
        return "https://api.lever.co/v1"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_debug(self) -> bool:
        """Check if debug mode is enabled (only in non-production)."""
        return self.debug_mode and not self.is_production


@lru_cache
def get_settings() -> Settings:
    """Get the application settings singleton.

    Uses lru_cache for efficient caching of the settings instance.

    Returns:
        Settings: The application settings instance.
    """
    return Settings()
