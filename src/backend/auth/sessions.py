"""Opaque login sessions with inactivity expiry for BLOOD-6."""

import hashlib
import secrets
import time

from sqlalchemy.orm import Session

from .models import AuthenticatedUser
from .orm import Account, LoginSession
from .service import AuthenticationError


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class SessionService:
    def __init__(self, session: Session, idle_timeout_seconds: int = 900):
        if idle_timeout_seconds <= 0:
            raise ValueError("Session timeout must be positive.")
        self.session = session
        self.idle_timeout_seconds = idle_timeout_seconds

    def create(self, user_id: int) -> str:
        account = self.session.get(Account, user_id)
        if account is None or not account.is_active or not account.is_verified:
            raise AuthenticationError("Authentication required.")

        token = secrets.token_urlsafe(32)
        self.session.add(LoginSession(
            token_hash=_token_hash(token),
            user_id=account.id,
            last_seen_at=int(time.time()),
        ))
        self.session.commit()
        return token

    def resolve(self, token: str) -> AuthenticatedUser:
        if not token or len(token) > 256:
            raise AuthenticationError("Authentication required.")

        login_session = self.session.get(LoginSession, _token_hash(token))
        if login_session is None:
            raise AuthenticationError("Authentication required.")

        now = int(time.time())
        account = self.session.get(Account, login_session.user_id)

        if (
            now - login_session.last_seen_at >= self.idle_timeout_seconds
            or account is None
            or not account.is_active
            or not account.is_verified
        ):
            self.session.delete(login_session)
            self.session.commit()
            raise AuthenticationError("Authentication required.")

        user = AuthenticatedUser(
            id=account.id,
            role=account.role,
            hospital_id=account.hospital_id,
        )
        login_session.last_seen_at = now
        self.session.commit()
        return user

    def revoke(self, token: str) -> None:
        login_session = self.session.get(LoginSession, _token_hash(token))
        if login_session is not None:
            self.session.delete(login_session)
            self.session.commit()
