"""Password hashing and verification for BLOOD-6."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Create an Argon2 hash. Store the result, never the plain password."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return True only when the supplied password matches the stored hash."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False
