"""API routes for integration settings management."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from applicant_validator.database.base import get_db_session
from applicant_validator.services.integration_settings import (
    get_integration_settings_service,
)
from applicant_validator.services.system_config import get_system_config_service

router = APIRouter(prefix="/settings", tags=["settings"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class IntegrationResponse(BaseModel):
    """Response model for a single integration."""

    provider: str
    display_name: str
    is_enabled: bool
    has_credentials: bool
    api_key_masked: str | None = None
    api_secret_masked: str | None = None
    account_id: str | None = None
    fraud_score_threshold: int | None = None
    monthly_usage: int
    monthly_limit: int | None = None
    last_test_at: str | None = None
    last_test_success: bool | None = None
    last_test_message: str | None = None
    notes: str | None = None
    config_json: str | None = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class IntegrationListResponse(BaseModel):
    """Response model for listing integrations."""

    integrations: list[IntegrationResponse]


class UpdateIntegrationRequest(BaseModel):
    """Request model for updating an integration."""

    is_enabled: bool | None = None
    api_key: str | None = Field(None, description="API key (empty string to clear)")
    api_secret: str | None = Field(None, description="API secret (empty string to clear)")
    account_id: str | None = Field(None, description="Account ID (empty string to clear)")
    fraud_score_threshold: int | None = Field(None, ge=0, le=100)
    notes: str | None = None
    config_json: str | None = Field(None, description="JSON configuration (provider-specific)")


class TestIntegrationResponse(BaseModel):
    """Response model for testing an integration."""

    success: bool
    message: str
    details: dict[str, Any] | None = None


class ValidationSettingsResponse(BaseModel):
    """Response model for validation settings."""

    mass_applicant_threshold: int = Field(
        description="Number of job applications that triggers mass applicant flag"
    )


class UpdateValidationSettingsRequest(BaseModel):
    """Request model for updating validation settings."""

    mass_applicant_threshold: int | None = Field(
        None,
        ge=2,
        le=50,
        description="Number of job applications that triggers mass applicant flag (2-50)",
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _integration_to_response(integration: Any) -> IntegrationResponse:
    """Convert IntegrationSetting model to response."""
    return IntegrationResponse(
        provider=integration.provider,
        display_name=integration.display_name,
        is_enabled=integration.is_enabled,
        has_credentials=integration.has_credentials,
        api_key_masked=integration.masked_api_key,
        api_secret_masked=integration.masked_api_secret,
        account_id=integration.account_id,
        fraud_score_threshold=integration.fraud_score_threshold,
        monthly_usage=integration.monthly_usage,
        monthly_limit=integration.monthly_limit,
        last_test_at=integration.last_test_at.isoformat() if integration.last_test_at else None,
        last_test_success=integration.last_test_success,
        last_test_message=integration.last_test_message,
        notes=integration.notes,
        config_json=integration.config_json,
    )


# =============================================================================
# Routes
# =============================================================================


@router.get("/integrations", response_model=IntegrationListResponse)
async def list_integrations(
    session: AsyncSession = Depends(get_db_session),
) -> IntegrationListResponse:
    """List all integration settings.

    Returns all configured integrations with their current status.
    API keys are masked for security.
    """
    service = await get_integration_settings_service(session)
    integrations = await service.get_all_integrations()

    return IntegrationListResponse(integrations=[_integration_to_response(i) for i in integrations])


@router.get("/integrations/{provider}", response_model=IntegrationResponse)
async def get_integration(
    provider: str,
    session: AsyncSession = Depends(get_db_session),
) -> IntegrationResponse:
    """Get settings for a specific integration.

    Args:
        provider: Integration provider name (e.g., 'ipqualityscore', 'twilio').
    """
    service = await get_integration_settings_service(session)
    integration = await service.get_integration(provider)

    if not integration:
        raise HTTPException(status_code=404, detail=f"Integration '{provider}' not found")

    return _integration_to_response(integration)


@router.patch("/integrations/{provider}", response_model=IntegrationResponse)
async def update_integration(
    provider: str,
    request: UpdateIntegrationRequest,
    session: AsyncSession = Depends(get_db_session),
) -> IntegrationResponse:
    """Update settings for a specific integration.

    Args:
        provider: Integration provider name.
        request: Fields to update.
    """
    service = await get_integration_settings_service(session)

    try:
        integration = await service.update_integration(
            provider,
            is_enabled=request.is_enabled,
            api_key=request.api_key,
            api_secret=request.api_secret,
            account_id=request.account_id,
            fraud_score_threshold=request.fraud_score_threshold,
            notes=request.notes,
            config_json=request.config_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return _integration_to_response(integration)


@router.post("/integrations/{provider}/test", response_model=TestIntegrationResponse)
async def test_integration(
    provider: str,
    session: AsyncSession = Depends(get_db_session),
) -> TestIntegrationResponse:
    """Test an integration by making a simple API call.

    Args:
        provider: Integration provider name.

    Returns:
        Test result with success status and message.
    """
    service = await get_integration_settings_service(session)
    result = await service.test_integration(provider)

    return TestIntegrationResponse(
        success=result["success"],
        message=result["message"],
        details=result.get("details"),
    )


@router.post("/integrations/{provider}/reset-usage")
async def reset_usage(
    provider: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Reset the monthly usage counter for an integration.

    Args:
        provider: Integration provider name.
    """
    service = await get_integration_settings_service(session)
    integration = await service.get_integration(provider)

    if not integration:
        raise HTTPException(status_code=404, detail=f"Integration '{provider}' not found")

    await service.reset_monthly_usage(provider)

    return {"status": "ok", "message": f"Usage reset for {provider}"}


# =============================================================================
# Validation Settings Routes
# =============================================================================


@router.get("/validation", response_model=ValidationSettingsResponse)
async def get_validation_settings(
    session: AsyncSession = Depends(get_db_session),
) -> ValidationSettingsResponse:
    """Get validation settings.

    Returns all configurable validation thresholds and settings.
    """
    config_service = get_system_config_service(session)
    settings = await config_service.get_all_validation_settings()

    return ValidationSettingsResponse(
        mass_applicant_threshold=settings.get("mass_applicant_threshold", 5),
    )


@router.patch("/validation", response_model=ValidationSettingsResponse)
async def update_validation_settings(
    request: UpdateValidationSettingsRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ValidationSettingsResponse:
    """Update validation settings.

    Args:
        request: Fields to update.

    Returns:
        Updated validation settings.
    """
    config_service = get_system_config_service(session)

    # Update mass applicant threshold if provided
    if request.mass_applicant_threshold is not None:
        await config_service.set("mass_applicant_threshold", request.mass_applicant_threshold)

    # Return updated settings
    settings = await config_service.get_all_validation_settings()

    return ValidationSettingsResponse(
        mass_applicant_threshold=settings.get("mass_applicant_threshold", 5),
    )
