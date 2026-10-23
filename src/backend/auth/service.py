"""Login verification and account lockout for BLOOD-6 and BLOOD-8."""

import time
from typing import Callable

from .models import AuthenticatedUser
from .repository import AccountRepository
from .security import hash_password, verify_password


_DUMMY_PASSWORD_HASH = hash_password("dummy-password-not-an-account")


class AuthenticationError(Exception):
    """Raised when login cannot be accepted."""


class AuthService:
    def __init__(
        self,
        repository: AccountRepository,
        *,
        clock: Callable[[], float] = time.time,
        max_failed_attempts: int = 5,
        lock_duration_seconds: int = 1800,
    ):
        if max_failed_attempts <= 0 or lock_duration_seconds <= 0:
            raise ValueError("Lockout settings must be positive.")
        self.repository = repository
        self.clock = clock
        self.max_failed_attempts = max_failed_attempts
        self.lock_duration_seconds = lock_duration_seconds

    def authenticate(self, email: str, password: str) -> AuthenticatedUser:
        account = self.repository.get_by_email(email)
        now = int(self.clock())

        if account is None:
            verify_password(password, _DUMMY_PASSWORD_HASH)
            raise AuthenticationError("Invalid email or password.")

        if not account.is_active or not account.is_verified:
            raise AuthenticationError("Invalid email or password.")

        if account.locked_until is not None:
            if now < account.locked_until:
                raise AuthenticationError("Invalid email or password.")
            account.locked_until = None
            account.failed_login_attempts = 0

        if not verify_password(password, account.password_hash):
            account.failed_login_attempts += 1
            if account.failed_login_attempts >= self.max_failed_attempts:
                account.locked_until = now + self.lock_duration_seconds
            self.repository.session.commit()
            raise AuthenticationError("Invalid email or password.")

        account.failed_login_attempts = 0
        account.locked_until = None
        self.repository.session.commit()

        return AuthenticatedUser(
            id=account.id,
            role=account.role,
            hospital_id=account.hospital_id,
        )
