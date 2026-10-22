"""One-time code generation and verification for signup."""

import secrets

from .security import hash_password, verify_password


def generate_otp() -> str:
    """Generate a six-digit code, preserving leading zeroes."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(code: str) -> str:
    """Store a hash of the code instead of the code itself."""
    if len(code) != 6 or not code.isdigit():
        raise ValueError("OTP must contain exactly six digits.")
    return hash_password(code)


def verify_otp(code: str, stored_hash: str) -> bool:
    """Check a supplied code against its stored hash."""
    if len(code) != 6 or not code.isdigit():
        return False
    return verify_password(code, stored_hash)
