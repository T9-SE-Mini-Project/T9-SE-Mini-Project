"""Login verification for BLOOD-6."""

from .models import AuthenticatedUser
from .repository import AccountRepository
from .security import hash_password, verify_password


# Used for unknown accounts so password verification still takes place.
_DUMMY_PASSWORD_HASH = hash_password("dummy-password-not-an-account")


class AuthenticationError(Exception):
    """Raised when login cannot be accepted."""


class AuthService:
    def __init__(self, repository: AccountRepository):
        self.repository = repository

    def authenticate(self, email: str, password: str) -> AuthenticatedUser:
        account = self.repository.get_by_email(email)

        stored_hash = (
            account.password_hash
            if account is not None
            else _DUMMY_PASSWORD_HASH
        )
        password_matches = verify_password(password, stored_hash)

        if (
            account is None
            or not password_matches
            or not account.is_active
            or not account.is_verified
        ):
            raise AuthenticationError("Invalid email or password.")

        return AuthenticatedUser(
            id=account.id,
            role=account.role,
            hospital_id=account.hospital_id,
        )
