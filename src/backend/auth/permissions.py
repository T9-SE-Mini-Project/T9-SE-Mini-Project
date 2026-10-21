"""Role-based permission checks for BLOOD-6."""

from .models import AuthenticatedUser, ROLES


class AuthorizationError(Exception):
    """The authenticated user is not permitted to perform this action."""


def check_role(
    user: AuthenticatedUser,
    *allowed_roles: str,
) -> AuthenticatedUser:
    """Allow only explicitly listed roles; admin has no automatic bypass."""
    if not allowed_roles:
        raise ValueError("At least one allowed role is required.")

    if any(role not in ROLES for role in allowed_roles):
        raise ValueError("Unknown role in permission configuration.")

    if user.role not in allowed_roles:
        raise AuthorizationError("You do not have permission for this action.")

    return user
