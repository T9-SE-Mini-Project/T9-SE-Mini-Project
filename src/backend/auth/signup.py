"""Donor signup and OTP verification for BLOOD-7."""

import time
from typing import Callable, Protocol

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .orm import Account, SignupOTP
from .otp import generate_otp, hash_otp, verify_otp
from .repository import AccountRepository, normalize_email
from .security import hash_password


class OTPSender(Protocol):
    """Implemented by the team's notification wrapper."""

    def send_otp(self, email: str, code: str) -> None:
        """Deliver the code without logging or returning it to the client."""


class SignupError(Exception):
    """Signup or verification could not be completed."""


class SignupService:
    def __init__(
        self,
        db: Session,
        sender: OTPSender,
        *,
        otp_lifetime_seconds: int = 300,
        max_attempts: int = 5,
        clock: Callable[[], float] = time.time,
    ):
        if otp_lifetime_seconds <= 0 or max_attempts <= 0:
            raise ValueError("OTP settings must be positive.")
        self.db = db
        self.sender = sender
        self.otp_lifetime_seconds = otp_lifetime_seconds
        self.max_attempts = max_attempts
        self.clock = clock

    def register_donor(self, email: str, password: str) -> None:
        address = normalize_email(email)
        if AccountRepository(self.db).get_by_email(address) is not None:
            raise SignupError("An account with this email already exists.")

        account = Account(
            email=address,
            password_hash=hash_password(password),
            role="donor",
            is_active=True,
            is_verified=False,
        )
        code = generate_otp()

        try:
            self.db.add(account)
            self.db.flush()
            self.db.add(SignupOTP(
                user_id=account.id,
                code_hash=hash_otp(code),
                expires_at=int(self.clock()) + self.otp_lifetime_seconds,
                attempts=0,
            ))
            self.sender.send_otp(address, code)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise SignupError(
                "An account with this email already exists."
            ) from exc
        except Exception:
            self.db.rollback()
            raise

    def verify_signup(self, email: str, code: str) -> None:
        account = AccountRepository(self.db).get_by_email(email)
        if account is None or account.is_verified:
            raise SignupError("Invalid or expired verification code.")

        pending = self.db.get(SignupOTP, account.id)
        if pending is None:
            raise SignupError("Invalid or expired verification code.")

        if int(self.clock()) >= pending.expires_at:
            self.db.delete(pending)
            self.db.commit()
            raise SignupError("Invalid or expired verification code.")

        if pending.attempts >= self.max_attempts:
            raise SignupError("Too many verification attempts.")

        if not verify_otp(code, pending.code_hash):
            pending.attempts += 1
            self.db.commit()
            raise SignupError("Invalid or expired verification code.")

        account.is_verified = True
        self.db.delete(pending)
        self.db.commit()

    def resend_otp(self, email: str) -> None:
        """Issue a fresh code after the previous one has expired."""
        account = AccountRepository(self.db).get_by_email(email)
        if account is None or account.is_verified:
            raise SignupError("Signup cannot be verified.")

        pending = self.db.get(SignupOTP, account.id)
        now = int(self.clock())

        if pending is not None and now < pending.expires_at:
            raise SignupError("Wait until the current code expires.")

        code = generate_otp()
        if pending is None:
            pending = SignupOTP(user_id=account.id)
            self.db.add(pending)

        pending.code_hash = hash_otp(code)
        pending.expires_at = now + self.otp_lifetime_seconds
        pending.attempts = 0

        try:
            self.sender.send_otp(account.email, code)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
