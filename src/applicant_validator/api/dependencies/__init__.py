"""API dependencies for route protection."""

from applicant_validator.api.dependencies.auth import (
    AdminUser,
    CurrentUser,
    OptionalUser,
    SuperAdminUser,
    get_current_user,
    get_current_user_optional,
    require_admin,
    require_superadmin,
)

__all__ = [
    "AdminUser",
    "CurrentUser",
    "OptionalUser",
    "SuperAdminUser",
    "get_current_user",
    "get_current_user_optional",
    "require_admin",
    "require_superadmin",
]
