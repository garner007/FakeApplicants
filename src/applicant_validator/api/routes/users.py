"""User management routes for admin users."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from applicant_validator.api.dependencies import AdminUser
from applicant_validator.database import User, UserRole, get_session
from applicant_validator.services.auth import (
    create_user,
    generate_temp_password,
    get_user_by_id,
    reset_user_password,
    revoke_all_user_sessions,
)

router = APIRouter(prefix="/users", tags=["users"])


# Request/Response schemas
class UserListResponse(BaseModel):
    """User list item."""

    id: str
    email: str
    name: str
    role: str
    is_active: bool
    must_change_password: bool
    last_login_at: str | None
    created_at: str


class UserDetailResponse(UserListResponse):
    """Detailed user response."""

    created_by_email: str | None


class CreateUserRequest(BaseModel):
    """Create user request body."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="user")


class CreateUserResponse(BaseModel):
    """Create user response with temporary password."""

    id: str
    email: str
    name: str
    role: str
    temp_password: str


class UpdateUserRequest(BaseModel):
    """Update user request body."""

    name: str | None = Field(default=None, max_length=255)
    role: str | None = None
    is_active: bool | None = None


class ResetPasswordResponse(BaseModel):
    """Password reset response."""

    temp_password: str
    message: str


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


def _validate_role(role: str, current_user: User, target_user: User | None = None) -> None:
    """Validate that the current user can assign the given role.

    Args:
        role: Role to assign.
        current_user: User making the request.
        target_user: User being modified (if applicable).

    Raises:
        HTTPException: If role assignment is not allowed.
    """
    # Validate role is valid
    try:
        UserRole(role)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {role}. Must be one of: {[r.value for r in UserRole]}",
        ) from err

    # Only superadmins can create/modify superadmins
    if role == UserRole.SUPERADMIN.value and not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can assign superadmin role",
        )

    # Only superadmins can modify other superadmins
    if target_user and target_user.is_superadmin and not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can modify superadmin accounts",
        )


@router.get("", response_model=list[UserListResponse])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: AdminUser,
) -> list[UserListResponse]:
    """List all users (admin only)."""
    result = await session.execute(
        select(User)
        .where(User.is_deleted == False)  # noqa: E712
        .order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    return [
        UserListResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
            created_at=user.created_at.isoformat(),
        )
        for user in users
    ]


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: AdminUser,
) -> UserDetailResponse:
    """Get a specific user by ID (admin only)."""
    user = await get_user_by_id(session, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get creator email if available
    created_by_email = None
    if user.created_by_id:
        creator = await get_user_by_id(session, user.created_by_id)
        if creator:
            created_by_email = creator.email

    return UserDetailResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat(),
        created_by_email=created_by_email,
    )


@router.post("", response_model=CreateUserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(
    body: CreateUserRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: AdminUser,
) -> CreateUserResponse:
    """Create a new user (admin only).

    Generates a temporary password that the user must change on first login.
    """
    # Validate role assignment
    _validate_role(body.role, current_user)

    # Generate temp password
    temp_password = generate_temp_password()

    try:
        user = await create_user(
            session,
            email=body.email,
            password=temp_password,
            name=body.name,
            role=UserRole(body.role),
            created_by=current_user,
            must_change_password=True,
        )
        await session.commit()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return CreateUserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        temp_password=temp_password,
    )


@router.patch("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: UUID,
    body: UpdateUserRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: AdminUser,
) -> UserDetailResponse:
    """Update a user (admin only).

    Admins cannot modify superadmins. Only superadmins can modify other superadmins.
    """
    user = await get_user_by_id(session, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-demotion from admin
    if user.id == current_user.id and body.role and body.role != current_user.role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    # Prevent self-deactivation
    if user.id == current_user.id and body.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    # Validate role if changing
    if body.role:
        _validate_role(body.role, current_user, user)
        user.role = body.role

    # Update fields
    if body.name is not None:
        user.name = body.name

    if body.is_active is not None:
        user.is_active = body.is_active
        # Revoke sessions if deactivating
        if not body.is_active:
            await revoke_all_user_sessions(session, user.id)

    await session.commit()

    # Get creator email
    created_by_email = None
    if user.created_by_id:
        creator = await get_user_by_id(session, user.created_by_id)
        if creator:
            created_by_email = creator.email

    return UserDetailResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat(),
        created_by_email=created_by_email,
    )


@router.delete("/{user_id}", response_model=MessageResponse)
async def deactivate_user(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: AdminUser,
) -> MessageResponse:
    """Deactivate a user (soft delete, admin only).

    This deactivates rather than deletes the user for audit purposes.
    """
    user = await get_user_by_id(session, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )

    # Only superadmins can deactivate other superadmins
    if user.is_superadmin and not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can deactivate superadmin accounts",
        )

    # Deactivate user
    user.is_active = False

    # Revoke all sessions
    await revoke_all_user_sessions(session, user.id)

    await session.commit()

    return MessageResponse(message=f"User {user.email} has been deactivated")


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: AdminUser,
) -> ResetPasswordResponse:
    """Reset a user's password to a temporary one (admin only).

    The user will need to change this password on next login.
    """
    user = await get_user_by_id(session, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Only superadmins can reset superadmin passwords
    if user.is_superadmin and not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can reset superadmin passwords",
        )

    # Reset password
    temp_password = await reset_user_password(session, user)
    await session.commit()

    return ResetPasswordResponse(
        temp_password=temp_password,
        message=f"Password for {user.email} has been reset. Change required on next login.",
    )
