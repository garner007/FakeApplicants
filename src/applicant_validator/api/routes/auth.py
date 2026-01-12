"""Authentication routes for login, logout, and password management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from applicant_validator.api.dependencies import CurrentUser
from applicant_validator.database import get_session
from applicant_validator.services.auth import (
    authenticate_user,
    change_password,
    complete_initial_setup,
    create_session,
    revoke_session,
    verify_password,
)
from applicant_validator.services.auth_settings import get_auth_settings_cache

router = APIRouter(prefix="/auth", tags=["auth"])


# Request/Response schemas
class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Login response."""

    id: str
    email: str
    name: str
    role: str
    must_change_password: bool
    must_change_email: bool


class UserResponse(BaseModel):
    """Current user response."""

    id: str
    email: str
    name: str
    role: str
    is_active: bool
    must_change_password: bool
    must_change_email: bool
    last_login_at: str | None


class ChangePasswordRequest(BaseModel):
    """Change password request body."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class InitialSetupRequest(BaseModel):
    """Initial setup request body (first login with default credentials)."""

    current_password: str = Field(..., min_length=1)
    new_email: str | None = Field(None, description="New email (required if must_change_email)")
    new_password: str = Field(..., min_length=8)


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


def _get_client_ip(request: Request) -> str | None:
    """Extract client IP from request."""
    # Check X-Forwarded-For for proxy setups
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _set_session_cookie(response: Response, token: str) -> None:
    """Set the session cookie on the response."""
    cache = get_auth_settings_cache()

    response.set_cookie(
        key=cache.cookie_name,
        value=token,
        httponly=True,
        secure=cache.cookie_secure,
        samesite="lax",
        max_age=cache.jwt_expiry_hours * 3600,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    """Clear the session cookie from the response."""
    cache = get_auth_settings_cache()

    response.delete_cookie(
        key=cache.cookie_name,
        path="/",
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LoginResponse:
    """Login with email and password.

    Sets an HTTP-only session cookie on successful authentication.
    """
    # Authenticate user
    user = await authenticate_user(session, body.email, body.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create session
    token, _ = await create_session(
        session,
        user,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    await session.commit()

    # Set cookie
    _set_session_cookie(response, token)

    return LoginResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        must_change_password=user.must_change_password,
        must_change_email=user.must_change_email,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: CurrentUser,
) -> MessageResponse:
    """Logout and revoke the current session."""
    cache = get_auth_settings_cache()

    # Get token from cookie to revoke the session
    token = request.cookies.get(cache.cookie_name)
    if token:
        from applicant_validator.services.auth import decode_jwt_token

        payload = decode_jwt_token(token)
        if payload:
            jti = payload.get("jti")
            if jti:
                await revoke_session(session, jti)
                await session.commit()

    # Clear cookie
    _clear_session_cookie(response)

    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
) -> UserResponse:
    """Get the current authenticated user's information."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        is_active=current_user.is_active,
        must_change_password=current_user.must_change_password,
        must_change_email=current_user.must_change_email,
        last_login_at=current_user.last_login_at.isoformat()
        if current_user.last_login_at
        else None,
    )


@router.post("/change-password", response_model=MessageResponse)
async def change_user_password(
    body: ChangePasswordRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: CurrentUser,
) -> MessageResponse:
    """Change the current user's password.

    Requires the current password for verification.
    """
    # Verify current password
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Check new password is different
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    # Change password
    await change_password(session, current_user, body.new_password)
    await session.commit()

    return MessageResponse(message="Password changed successfully")


@router.post("/initial-setup", response_model=MessageResponse)
async def initial_setup(
    body: InitialSetupRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: CurrentUser,
) -> MessageResponse:
    """Complete initial account setup (change email and password on first login).

    This endpoint is used when a user has must_change_password or must_change_email
    flags set (e.g., after account creation with default credentials).
    """
    # Verify current password
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Check new password is different
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    # Validate email is provided if required
    if current_user.must_change_email and not body.new_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New email is required",
        )

    # Complete setup
    try:
        await complete_initial_setup(
            session,
            current_user,
            new_email=body.new_email,
            new_password=body.new_password,
        )
        await session.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return MessageResponse(message="Account setup completed successfully")
