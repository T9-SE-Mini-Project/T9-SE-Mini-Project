"""BLOOD-7: donor signup and OTP verification through HTTP."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.backend.auth.dependencies import create_auth_dependencies
from src.backend.auth.orm import Account, AuthBase, SignupOTP
from src.backend.auth.routes import create_router
from src.backend.auth.signup_routes import create_signup_router


class FakeSender:
    def __init__(self):
        self.sent = []

    def send_otp(self, email, code):
        self.sent.append((email, code))


@pytest.fixture
def setup_api():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)
    sender = FakeSender()

    def get_session():
        with Session(engine) as db:
            yield db

    get_current_user, _ = create_auth_dependencies(get_session)
    app = FastAPI()
    app.include_router(create_router(get_session, get_current_user))
    app.include_router(create_signup_router(get_session, sender))

    with TestClient(app) as client:
        yield client, sender, engine

    engine.dispose()


def test_signup_requires_correct_otp_before_login(setup_api):
    client, sender, engine = setup_api
    password = "ExamplePassword123!"

    response = client.post("/api/auth/signup", json={
        "email": "Donor@Example.com",
        "password": password,
    })
    assert response.status_code == 202, response.text
    assert len(sender.sent) == 1
    email, code = sender.sent[0]
    assert email == "donor@example.com"
    assert len(code) == 6 and code.isdigit()
    assert code not in response.text

    with Session(engine) as db:
        account = db.query(Account).filter_by(email=email).one()
        assert account.role == "donor"
        assert not account.is_verified
        assert db.get(SignupOTP, account.id).code_hash != code

    login = client.post("/api/auth/login", json={
        "email": email, "password": password,
    })
    assert login.status_code == 401

    wrong = client.post("/api/auth/signup/verify", json={
        "email": email, "code": "abcdef",
    })
    assert wrong.status_code == 422

    correct = client.post("/api/auth/signup/verify", json={
        "email": email, "code": code,
    })
    assert correct.status_code == 200, correct.text

    login = client.post("/api/auth/login", json={
        "email": email, "password": password,
    })
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "donor"

    reused = client.post("/api/auth/signup/verify", json={
        "email": email, "code": code,
    })
    assert reused.status_code == 400


def test_duplicate_signup_and_early_resend_are_rejected(setup_api):
    client, sender, _ = setup_api
    payload = {
        "email": "donor@example.com",
        "password": "ExamplePassword123!",
    }
    assert client.post("/api/auth/signup", json=payload).status_code == 202

    duplicate = client.post("/api/auth/signup", json=payload)
    assert duplicate.status_code == 409

    early_resend = client.post("/api/auth/signup/resend", json={
        "email": payload["email"],
    })
    assert early_resend.status_code == 400
    assert len(sender.sent) == 1


def test_public_signup_cannot_choose_a_privileged_role(setup_api):
    client, _, engine = setup_api
    response = client.post("/api/auth/signup", json={
        "email": "staff@example.com",
        "password": "ExamplePassword123!",
        "role": "admin",
    })
    assert response.status_code == 202

    with Session(engine) as db:
        account = db.query(Account).filter_by(
            email="staff@example.com"
        ).one()
        assert account.role == "donor"
        assert not account.is_verified
