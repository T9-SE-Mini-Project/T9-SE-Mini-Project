"""FastAPI authentication and role-check dependencies."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import ROLES
from .permissions import AuthorizationError, check_role
from .service import AuthenticationError
from .sessions import SessionService


_bearer = HTTPBearer(auto_error=False)


def get_session_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def create_auth_dependencies(get_session, idle_timeout_seconds=900):
    """Build dependencies using an auth database-session provider."""

    def get_current_user(
        token: str = Depends(get_session_token),
        db=Depends(get_session),
    ):
        try:
            return SessionService(db, idle_timeout_seconds).resolve(token)
        except AuthenticationError as exc:
            raise HTTPException(
                status_code=401,
                detail="Authentication required.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    def require_role(*allowed_roles):
        if not allowed_roles or any(role not in ROLES for role in allowed_roles):
            raise ValueError("Configure at least one valid allowed role.")

        def role_dependency(user=Depends(get_current_user)):
            try:
                return check_role(user, *allowed_roles)
            except AuthorizationError as exc:
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission for this action.",
                ) from exc

        return role_dependency

    return get_current_user, require_role
