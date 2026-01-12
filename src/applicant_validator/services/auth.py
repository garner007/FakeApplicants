"""Authentication service for user management.

Handles password hashing, JWT token generation, and session management.
Auth settings are read from the database via AuthSettingsCache.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt  # type: ignore[import-untyped]
from passlib.context import CryptContext  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from applicant_validator.database import User, UserRole, UserSession
from applicant_validator.services.auth_settings import get_auth_settings_cache

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT algorithm
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password.

    Returns:
        Hashed password string.
    """
    result: str = pwd_context.hash(password)
    return result


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash.

    Args:
        plain_password: Plain text password to verify.
        hashed_password: Hashed password to compare against.

    Returns:
        True if password matches, False otherwise.
    """
    result: bool = pwd_context.verify(plain_password, hashed_password)
    return result


def validate_email_domain(email: str) -> bool:
    """Validate that an email matches the allowed domain.

    Args:
        email: Email address to validate.

    Returns:
        True if email domain is allowed, False otherwise.
    """
    cache = get_auth_settings_cache()

    # If no domain restriction, allow all
    if not cache.allowed_domain:
        return True

    # Check domain
    if "@" not in email:
        return False

    domain = email.split("@")[1].lower()
    allowed_domain = cache.allowed_domain.lower()

    return domain == allowed_domain


def generate_temp_password(length: int = 16) -> str:
    """Generate a random temporary password.

    Args:
        length: Length of password to generate.

    Returns:
        Random password string.
    """
    # Use URL-safe characters for easy copy/paste
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_jwt_token(user_id: str, jti: str) -> str:
    """Create a JWT token for a user.

    Args:
        user_id: User ID to encode in token.
        jti: JWT ID for session tracking.

    Returns:
        Encoded JWT token string.
    """
    cache = get_auth_settings_cache()

    expires = datetime.now(UTC) + timedelta(hours=cache.jwt_expiry_hours)

    payload = {
        "sub": user_id,
        "jti": jti,
        "exp": expires,
        "iat": datetime.now(UTC),
    }

    result: str = jwt.encode(payload, cache.jwt_secret, algorithm=ALGORITHM)
    return result


def decode_jwt_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token.

    Args:
        token: JWT token string.

    Returns:
        Decoded payload dict or None if invalid.
    """
    cache = get_auth_settings_cache()

    try:
        payload: dict[str, Any] = jwt.decode(token, cache.jwt_secret, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Get a user by email address.

    Args:
        session: Database session.
        email: Email address to search for.

    Returns:
        User instance or None if not found.
    """
    result = await session.execute(
        select(User).where(User.email == email.lower(), User.is_deleted == False)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Get a user by ID.

    Args:
        session: Database session.
        user_id: User UUID.

    Returns:
        User instance or None if not found.
    """
    result = await session.execute(
        select(User).where(User.id == user_id, User.is_deleted == False)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> User | None:
    """Authenticate a user by email and password.

    Args:
        session: Database session.
        email: User email.
        password: Plain text password.

    Returns:
        User instance if authenticated, None otherwise.
    """
    user = await get_user_by_email(session, email)

    if not user:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


async def create_session(
    session: AsyncSession,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, UserSession]:
    """Create a new session for a user.

    Args:
        session: Database session.
        user: User to create session for.
        ip_address: Client IP address.
        user_agent: Client user agent string.

    Returns:
        Tuple of (JWT token, UserSession).
    """
    cache = get_auth_settings_cache()

    # Generate unique JWT ID
    jti = str(uuid.uuid4())

    # Calculate expiry
    expires_at = datetime.now(UTC) + timedelta(hours=cache.jwt_expiry_hours)

    # Create session record
    user_session = UserSession(
        user_id=user.id,
        jti=jti,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent[:500] if user_agent else None,
    )
    session.add(user_session)

    # Update user last login
    user.last_login_at = datetime.now(UTC)

    await session.flush()

    # Generate JWT token
    token = create_jwt_token(str(user.id), jti)

    return token, user_session


async def validate_session(
    session: AsyncSession,
    jti: str,
) -> UserSession | None:
    """Validate a session by JTI.

    Args:
        session: Database session.
        jti: JWT ID to validate.

    Returns:
        UserSession if valid, None otherwise.
    """
    result = await session.execute(
        select(UserSession).where(
            UserSession.jti == jti,
            UserSession.is_revoked == False,  # noqa: E712
            UserSession.expires_at > datetime.now(UTC),
        )
    )
    return result.scalar_one_or_none()


async def revoke_session(
    session: AsyncSession,
    jti: str,
) -> bool:
    """Revoke a session by JTI.

    Args:
        session: Database session.
        jti: JWT ID to revoke.

    Returns:
        True if session was revoked, False if not found.
    """
    result = await session.execute(select(UserSession).where(UserSession.jti == jti))
    user_session = result.scalar_one_or_none()

    if not user_session:
        return False

    user_session.is_revoked = True
    user_session.revoked_at = datetime.now(UTC)

    return True


async def revoke_all_user_sessions(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    """Revoke all sessions for a user.

    Args:
        session: Database session.
        user_id: User ID whose sessions to revoke.

    Returns:
        Number of sessions revoked.
    """
    result = await session.execute(
        select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_revoked == False,  # noqa: E712
        )
    )
    sessions = result.scalars().all()

    now = datetime.now(UTC)
    count = 0
    for user_session in sessions:
        user_session.is_revoked = True
        user_session.revoked_at = now
        count += 1

    return count


async def create_user(
    session: AsyncSession,
    email: str,
    password: str,
    name: str,
    role: UserRole = UserRole.USER,
    created_by: User | None = None,
    must_change_password: bool = True,
    first_name: str | None = None,
    last_name: str | None = None,
) -> User:
    """Create a new user.

    Args:
        session: Database session.
        email: User email (will be lowercased).
        password: Plain text password (will be hashed).
        name: User display name.
        role: User role (default USER).
        created_by: Admin user who created this user.
        must_change_password: Whether user must change password on first login.
        first_name: Optional first name.
        last_name: Optional last name.

    Returns:
        Created User instance.

    Raises:
        ValueError: If email domain is not allowed or email already exists.
    """
    # Validate email domain
    if not validate_email_domain(email):
        cache = get_auth_settings_cache()
        raise ValueError(f"Email must be from domain: {cache.allowed_domain}")

    # Check if email already exists
    existing = await get_user_by_email(session, email)
    if existing:
        raise ValueError("Email already registered")

    # Create user
    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        name=name,
        first_name=first_name,
        last_name=last_name,
        role=role.value,
        created_by_id=created_by.id if created_by else None,
        must_change_password=must_change_password,
    )
    session.add(user)
    await session.flush()

    return user


async def change_password(
    _session: AsyncSession,
    user: User,
    new_password: str,
) -> None:
    """Change a user's password.

    Args:
        session: Database session.
        user: User to update.
        new_password: New plain text password.
    """
    user.password_hash = hash_password(new_password)
    user.must_change_password = False


async def change_email(
    session: AsyncSession,
    user: User,
    new_email: str,
) -> None:
    """Change a user's email.

    Args:
        session: Database session.
        user: User to update.
        new_email: New email address.

    Raises:
        ValueError: If email domain is not allowed or email already exists.
    """
    # Validate email domain
    if not validate_email_domain(new_email):
        cache = get_auth_settings_cache()
        raise ValueError(f"Email must be from domain: {cache.allowed_domain}")

    # Check if email already exists (and it's not the same user)
    existing = await get_user_by_email(session, new_email)
    if existing and existing.id != user.id:
        raise ValueError("Email already registered")

    user.email = new_email.lower()
    user.must_change_email = False


async def complete_initial_setup(
    session: AsyncSession,
    user: User,
    new_email: str | None,
    new_password: str,
) -> None:
    """Complete initial account setup (change email and/or password).

    Used when a user has must_change_password or must_change_email flags set.

    Args:
        session: Database session.
        user: User to update.
        new_email: New email (required if must_change_email is True).
        new_password: New password.

    Raises:
        ValueError: If email change is required but not provided, or validation fails.
    """
    # Handle email change if required
    if user.must_change_email:
        if not new_email:
            raise ValueError("Email change is required")
        await change_email(session, user, new_email)

    # Always change password
    await change_password(session, user, new_password)


async def reset_user_password(
    session: AsyncSession,
    user: User,
) -> str:
    """Reset a user's password to a temporary one.

    Args:
        session: Database session.
        user: User to reset.

    Returns:
        The new temporary password.
    """
    temp_password = generate_temp_password()
    user.password_hash = hash_password(temp_password)
    user.must_change_password = True

    # Revoke all existing sessions
    await revoke_all_user_sessions(session, user.id)

    return temp_password
