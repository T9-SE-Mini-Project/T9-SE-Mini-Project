"""BLOOD-6: HTTP login, permissions, session, and logout tests."""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.backend.auth.dependencies import create_auth_dependencies
from src.backend.auth.models import ROLES
from src.backend.auth.orm import Account, AuthBase
from src.backend.auth.routes import create_router
from src.backend.auth.security import hash_password


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)

    with Session(engine) as db:
        password_hash = hash_password("ExamplePassword123!")
        for role in ROLES:
            db.add(Account(
                email=f"{role}@example.com",
                password_hash=password_hash,
                role=role,
                hospital_id=10 if role == "hospital_rep" else None,
                is_verified=True,
            ))
        db.add(Account(
            email="unverified@example.com",
            password_hash=password_hash,
            role="donor",
            is_verified=False,
        ))
        db.commit()

    def get_session():
        with Session(engine) as db:
            yield db

    get_current_user, require_role = create_auth_dependencies(get_session)
    app = FastAPI()
    app.include_router(create_router(get_session, get_current_user))

    @app.get("/test/staff")
    def staff_only(user=Depends(require_role("blood_bank_staff"))):
        return {"role": user.role}

    @app.get("/test/admin")
    def admin_only(user=Depends(require_role("admin"))):
        return {"role": user.role}

    with TestClient(app) as test_client:
        yield test_client

    engine.dispose()


def login(client, email, password="ExamplePassword123!"):
    return client.post("/api/auth/login", json={
        "email": email,
        "password": password,
    })


@pytest.mark.parametrize("role", ROLES)
def test_each_role_logs_in_and_sees_its_own_identity(client, role):
    response = login(client, f"{role}@example.com")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["user"]["role"] == role
    assert "password_hash" not in response.json()["user"]

    token = response.json()["access_token"]
    identity = client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}",
    })
    assert identity.status_code == 200
    assert identity.json()["role"] == role
    if role == "hospital_rep":
        assert identity.json()["hospital_id"] == 10


@pytest.mark.parametrize("email,password", [
    ("donor@example.com", "wrong-password"),
    ("missing@example.com", "ExamplePassword123!"),
    ("unverified@example.com", "ExamplePassword123!"),
])
def test_login_rejects_invalid_or_unverified_accounts(client, email, password):
    response = login(client, email, password)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_staff_and_admin_routes_enforce_roles(client):
    for role in ROLES:
        token = login(client, f"{role}@example.com").json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        staff = client.get("/test/staff", headers=headers)
        admin = client.get("/test/admin", headers=headers)

        assert staff.status_code == (200 if role == "blood_bank_staff" else 403)
        assert admin.status_code == (200 if role == "admin" else 403)


def test_missing_or_fabricated_token_cannot_access_identity(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={
        "Authorization": "Bearer fabricated-token",
    }).status_code == 401


def test_logout_revokes_session(client):
    token = login(client, "donor@example.com").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/auth/me", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401
