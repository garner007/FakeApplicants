"""Admin API routes for administrative operations."""

from datetime import UTC, datetime
from enum import Enum

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from applicant_validator.api.dependencies.auth import AdminUser
from applicant_validator.database import (
    Applicant,
    ApplicantSource,
    AuditLog,
    AuditLogChange,
    Flag,
    FlagEvidence,
    FlagType,
    LinkedInCertification,
    LinkedInEducation,
    LinkedInExperience,
    LinkedInProfile,
    LinkedInSkill,
    ValidationResult,
    ValidationResultEvidence,
    ValidationRun,
    ValidationRunConfig,
    get_session,
)
from applicant_validator.services.auth_settings import (
    AUTH_SETTING_KEYS,
    get_all_auth_settings,
    get_auth_settings_cache,
    set_auth_setting,
)

router = APIRouter(prefix="/admin", tags=["admin"])


class PurgeStatus(str, Enum):
    """Status of a purge operation."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PurgeState:
    """Global purge state tracker."""

    status: PurgeStatus = PurgeStatus.IDLE
    message: str = ""
    last_run_at: datetime | None = None
    error: str | None = None

    # Results tracking
    applicants_deleted: int = 0
    flags_deleted: int = 0
    validation_runs_deleted: int = 0


# Global purge state
_purge_state = PurgeState()


class PurgeRequest(BaseModel):
    """Request to purge the database."""

    confirm: bool = Field(
        ...,
        description="Must be True to confirm the purge operation",
    )
    keep_flag_types: bool = Field(
        default=True,
        description="Keep flag type definitions (recommended)",
    )


class PurgeStatusResponse(BaseModel):
    """Response with current purge status."""

    status: PurgeStatus
    message: str
    last_run_at: datetime | None
    error: str | None = None
    applicants_deleted: int
    flags_deleted: int
    validation_runs_deleted: int


class PurgeResponse(BaseModel):
    """Response after starting a purge."""

    message: str
    status: PurgeStatus


class DatabaseStatsResponse(BaseModel):
    """Database statistics response."""

    applicants_count: int
    flags_count: int
    validation_runs_count: int
    flag_types_count: int
    linkedin_profiles_count: int


async def _perform_purge(keep_flag_types: bool = True) -> None:
    """Perform the actual purge operation."""
    try:
        _purge_state.status = PurgeStatus.RUNNING
        _purge_state.message = "Starting database purge..."
        _purge_state.error = None
        _purge_state.applicants_deleted = 0
        _purge_state.flags_deleted = 0
        _purge_state.validation_runs_deleted = 0

        async with get_session() as session:
            # Count items before deletion
            applicant_count = await session.scalar(select(func.count(Applicant.id)))
            flag_count = await session.scalar(select(func.count(Flag.id)))
            validation_run_count = await session.scalar(select(func.count(ValidationRun.id)))

            _purge_state.message = "Deleting flag data..."

            # Delete in order to respect foreign key constraints
            # 1. Delete flag evidence first
            await session.execute(delete(FlagEvidence))

            # 2. Delete flags (must be before validation_runs due to FK)
            await session.execute(delete(Flag))

            # 3. Optionally delete flag types
            if not keep_flag_types:
                await session.execute(delete(FlagType))

            _purge_state.message = "Deleting validation data..."

            # 4. Delete validation result evidence
            await session.execute(delete(ValidationResultEvidence))

            # 5. Delete validation results
            await session.execute(delete(ValidationResult))

            # 6. Delete validation run configs
            await session.execute(delete(ValidationRunConfig))

            # 7. Delete validation runs
            await session.execute(delete(ValidationRun))

            _purge_state.message = "Deleting LinkedIn data..."

            # 8. Delete LinkedIn related data
            await session.execute(delete(LinkedInSkill))
            await session.execute(delete(LinkedInCertification))
            await session.execute(delete(LinkedInEducation))
            await session.execute(delete(LinkedInExperience))
            await session.execute(delete(LinkedInProfile))

            _purge_state.message = "Deleting applicant data..."

            # 9. Delete audit log changes
            await session.execute(delete(AuditLogChange))

            # 10. Delete audit logs
            await session.execute(delete(AuditLog))

            # 11. Delete applicant sources
            await session.execute(delete(ApplicantSource))

            # 12. Delete applicants
            await session.execute(delete(Applicant))

            await session.commit()

            # Update stats
            _purge_state.applicants_deleted = applicant_count or 0
            _purge_state.flags_deleted = flag_count or 0
            _purge_state.validation_runs_deleted = validation_run_count or 0

        _purge_state.status = PurgeStatus.COMPLETED
        _purge_state.message = (
            f"Purge complete: {_purge_state.applicants_deleted} applicants, "
            f"{_purge_state.flags_deleted} flags, "
            f"{_purge_state.validation_runs_deleted} validation runs deleted"
        )
        _purge_state.last_run_at = datetime.now(UTC)

    except Exception as e:
        _purge_state.status = PurgeStatus.FAILED
        _purge_state.error = str(e)
        _purge_state.message = f"Purge failed: {e!s}"


@router.get("/stats", response_model=DatabaseStatsResponse)
async def get_database_stats() -> DatabaseStatsResponse:
    """Get database statistics."""
    async with get_session() as session:
        applicants_count = await session.scalar(select(func.count(Applicant.id))) or 0
        flags_count = await session.scalar(select(func.count(Flag.id))) or 0
        validation_runs_count = await session.scalar(select(func.count(ValidationRun.id))) or 0
        flag_types_count = await session.scalar(select(func.count(FlagType.id))) or 0
        linkedin_profiles_count = await session.scalar(select(func.count(LinkedInProfile.id))) or 0

        return DatabaseStatsResponse(
            applicants_count=applicants_count,
            flags_count=flags_count,
            validation_runs_count=validation_runs_count,
            flag_types_count=flag_types_count,
            linkedin_profiles_count=linkedin_profiles_count,
        )


@router.get("/purge/status", response_model=PurgeStatusResponse)
async def get_purge_status() -> PurgeStatusResponse:
    """Get the current purge operation status."""
    return PurgeStatusResponse(
        status=_purge_state.status,
        message=_purge_state.message,
        last_run_at=_purge_state.last_run_at,
        error=_purge_state.error,
        applicants_deleted=_purge_state.applicants_deleted,
        flags_deleted=_purge_state.flags_deleted,
        validation_runs_deleted=_purge_state.validation_runs_deleted,
    )


@router.post("/purge", response_model=PurgeResponse)
async def purge_database(
    request: PurgeRequest,
    background_tasks: BackgroundTasks,
) -> PurgeResponse:
    """Purge all data from the database.

    WARNING: This operation is irreversible and will delete all applicants,
    flags, validation runs, and related data.
    """
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to execute purge",
        )

    if _purge_state.status == PurgeStatus.RUNNING:
        raise HTTPException(
            status_code=409,
            detail="Purge operation already in progress",
        )

    # Reset state and start purge in background
    _purge_state.status = PurgeStatus.RUNNING
    _purge_state.message = "Starting purge..."
    _purge_state.error = None

    background_tasks.add_task(_perform_purge, request.keep_flag_types)

    return PurgeResponse(
        message="Database purge started",
        status=PurgeStatus.RUNNING,
    )


# Auth Settings Models
class AuthSettingsResponse(BaseModel):
    """Auth settings response."""

    auth_allowed_domain: str = Field(description="Email domain restriction (empty = allow all)")
    auth_jwt_expiry_hours: str = Field(description="JWT token expiry in hours")
    auth_cookie_name: str = Field(description="Session cookie name")
    auth_cookie_secure: str = Field(description="Require HTTPS for cookies (true/false)")
    auth_min_password_length: str = Field(description="Minimum password length")


class AuthSettingsUpdate(BaseModel):
    """Auth settings update request."""

    auth_allowed_domain: str | None = None
    auth_jwt_expiry_hours: str | None = None
    auth_cookie_name: str | None = None
    auth_cookie_secure: str | None = None
    auth_min_password_length: str | None = None


@router.get("/auth-settings", response_model=AuthSettingsResponse)
async def get_auth_settings(
    admin_user: AdminUser,  # Require admin access
) -> AuthSettingsResponse:
    """Get all auth settings.

    Requires admin privileges.
    Note: JWT secret is not exposed through this endpoint.
    """
    async with get_session() as session:
        settings = await get_all_auth_settings(session)
        return AuthSettingsResponse(**settings)


@router.patch("/auth-settings", response_model=AuthSettingsResponse)
async def update_auth_settings(
    request: AuthSettingsUpdate,
    admin_user: AdminUser,  # Require admin access
) -> AuthSettingsResponse:
    """Update auth settings.

    Requires admin privileges.
    Only provided fields will be updated.
    Note: JWT secret cannot be modified through this endpoint.
    """
    async with get_session() as session:
        # Update only provided fields
        updates = request.model_dump(exclude_none=True)

        for key, value in updates.items():
            if key not in AUTH_SETTING_KEYS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid setting key: {key}",
                )
            # Validate values
            if key == "auth_jwt_expiry_hours":
                try:
                    hours = int(value)
                    if hours < 1 or hours > 8760:  # Max 1 year
                        raise ValueError("Hours must be between 1 and 8760")
                except ValueError as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid value for {key}: {e}",
                    ) from e
            elif key == "auth_min_password_length":
                try:
                    length = int(value)
                    if length < 6 or length > 128:
                        raise ValueError("Password length must be between 6 and 128")
                except ValueError as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid value for {key}: {e}",
                    ) from e
            elif key == "auth_cookie_secure":
                if value.lower() not in ("true", "false"):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid value for {key}: must be 'true' or 'false'",
                    )

            await set_auth_setting(session, key, value)

        await session.commit()

        # Refresh cache
        all_settings = await get_all_auth_settings(session)
        cache = get_auth_settings_cache()
        cache.refresh_sync(all_settings)

        return AuthSettingsResponse(**all_settings)
