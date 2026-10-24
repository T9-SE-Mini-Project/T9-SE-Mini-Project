"""BLOOD-8: five wrong passwords trigger a 30-minute account lock."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.backend.auth.orm import Account, AuthBase
from src.backend.auth.repository import AccountRepository
from src.backend.auth.security import hash_password
from src.backend.auth.service import AuthService, AuthenticationError


@pytest.fixture
def login_setup():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    AuthBase.metadata.create_all(engine)
    now = [1000]

    with Session(engine) as db:
        account = Account(
            email="donor@example.com",
            password_hash=hash_password("CorrectPassword123!"),
            role="donor",
            is_verified=True,
        )
        db.add(account)
        db.commit()

        service = AuthService(
            AccountRepository(db),
            clock=lambda: now[0],
        )
        yield service, account, now

    engine.dispose()


def test_fifth_wrong_password_locks_for_thirty_minutes(login_setup):
    service, account, now = login_setup

    for attempt in range(1, 6):
        with pytest.raises(AuthenticationError):
            service.authenticate("donor@example.com", "WrongPassword!")
        assert account.failed_login_attempts == attempt

    assert account.locked_until == 1000 + 1800

    with pytest.raises(AuthenticationError):
        service.authenticate("donor@example.com", "CorrectPassword123!")
    assert account.failed_login_attempts == 5

    now[0] = 2799
    with pytest.raises(AuthenticationError):
        service.authenticate("donor@example.com", "CorrectPassword123!")

    now[0] = 2800
    assert service.authenticate(
        "donor@example.com", "CorrectPassword123!"
    ).role == "donor"
    assert account.failed_login_attempts == 0
    assert account.locked_until is None


def test_successful_login_resets_consecutive_failures(login_setup):
    service, account, _ = login_setup

    for _ in range(4):
        with pytest.raises(AuthenticationError):
            service.authenticate("donor@example.com", "WrongPassword!")

    assert service.authenticate(
        "donor@example.com", "CorrectPassword123!"
    ).role == "donor"
    assert account.failed_login_attempts == 0

    with pytest.raises(AuthenticationError):
        service.authenticate("donor@example.com", "WrongPassword!")
    assert account.failed_login_attempts == 1
    assert account.locked_until is None


def test_failed_attempt_after_lock_expires_starts_new_count(login_setup):
    service, account, now = login_setup

    for _ in range(5):
        with pytest.raises(AuthenticationError):
            service.authenticate("donor@example.com", "WrongPassword!")

    now[0] = 2800
    with pytest.raises(AuthenticationError):
        service.authenticate("donor@example.com", "WrongPassword!")

    assert account.failed_login_attempts == 1
    assert account.locked_until is None


def test_http_login_rejects_correct_password_after_five_failures():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy.pool import StaticPool

    from src.backend.auth.dependencies import create_auth_dependencies
    from src.backend.auth.routes import create_router

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)

    with Session(engine) as db:
        db.add(Account(
            email="donor@example.com",
            password_hash=hash_password("CorrectPassword123!"),
            role="donor",
            is_verified=True,
        ))
        db.commit()

    def get_session():
        with Session(engine) as db:
            yield db

    get_current_user, _ = create_auth_dependencies(get_session)
    app = FastAPI()
    app.include_router(create_router(get_session, get_current_user))

    with TestClient(app) as client:
        for _ in range(5):
            response = client.post("/api/auth/login", json={
                "email": "donor@example.com",
                "password": "WrongPassword!",
            })
            assert response.status_code == 401

        response = client.post("/api/auth/login", json={
            "email": "donor@example.com",
            "password": "CorrectPassword123!",
        })
        assert response.status_code == 401

    with Session(engine) as db:
        account = db.query(Account).filter_by(
            email="donor@example.com"
        ).one()
        assert account.failed_login_attempts == 5
        assert account.locked_until is not None

    engine.dispose()
