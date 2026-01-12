"""Authentication dependencies for route protection."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from applicant_validator.database import User, get_db_session
from applicant_validator.services.auth import (
    decode_jwt_token,
    get_user_by_id,
    validate_session,
)
from applicant_validator.services.auth_settings import get_auth_settings_cache


async def get_current_user_optional(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User | None:
    """Get the current user from the session cookie if authenticated.

    This dependency does not raise an error if not authenticated.

    Args:
        request: FastAPI request object.
        session: Database session.

    Returns:
        User instance or None if not authenticated.
    """
    cache = get_auth_settings_cache()

    # Get token from cookie
    token = request.cookies.get(cache.cookie_name)
    if not token:
        return None

    # Decode token
    payload = decode_jwt_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    jti = payload.get("jti")

    if not user_id or not jti:
        return None

    # Validate session is still active
    user_session = await validate_session(session, jti)
    if not user_session:
        return None

    # Get user and validate
    try:
        from uuid import UUID

        user = await get_user_by_id(session, UUID(user_id))
        if user and user.is_active:
            return user
    except (ValueError, TypeError):
        pass

    return None


async def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    """Require authentication and return the current user.

    Raises 401 if not authenticated.

    Args:
        user: User from optional dependency.

    Returns:
        Authenticated User instance.

    Raises:
        HTTPException: 401 if not authenticated.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require admin privileges.

    Raises 403 if user is not admin or superadmin.

    Args:
        user: Current authenticated user.

    Returns:
        User instance if admin.

    Raises:
        HTTPException: 403 if not admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


async def require_superadmin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require superadmin privileges.

    Raises 403 if user is not superadmin.

    Args:
        user: Current authenticated user.

    Returns:
        User instance if superadmin.

    Raises:
        HTTPException: 403 if not superadmin.
    """
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin privileges required",
        )
    return user


# Type aliases for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
AdminUser = Annotated[User, Depends(require_admin)]
SuperAdminUser = Annotated[User, Depends(require_superadmin)]
