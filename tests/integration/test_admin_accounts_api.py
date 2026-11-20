"""Admin account management through the wired app: POST /api/admin/accounts.

Staff, hospital and admin accounts cannot sign up; an admin creates them. These tests
cover the rules in src/backend/auth/accounts.py that the other integration tests skip
because they insert accounts straight into the database.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.backend.auth.orm import Account
from src.backend.auth.security import hash_password
from src.backend.config import AppSettings
from src.backend.database import create_db_engine
from src.backend.main import create_app

PASSWORD = "ExamplePassword123!"
ADMIN = "admin.accounts@example.com"
STAFF = "staff.accounts@example.com"


@pytest.fixture
def client(tmp_path):
    settings = AppSettings(database_url=f"sqlite:///{tmp_path / 'bbms.db'}")
    app = create_app(settings)
    with TestClient(app) as test_client:
        engine = create_db_engine(settings.database_url)
        with Session(engine) as db:
            db.add_all([
                Account(email=ADMIN, password_hash=hash_password(PASSWORD), role="admin", is_verified=True),
                Account(email=STAFF, password_hash=hash_password(PASSWORD), role="blood_bank_staff", is_verified=True),
            ])
            db.commit()
        engine.dispose()
        yield test_client


def login(client, email, password=PASSWORD):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create(client, headers, **body):
    return client.post("/api/admin/accounts", headers=headers, json={"password": PASSWORD, **body})


def test_admin_creates_accounts_that_can_log_in_with_their_role(client):
    admin = login(client, ADMIN)
    for email, role, hospital_id in [
        ("new.staff@example.com", "blood_bank_staff", None),
        ("new.hospital@example.com", "hospital_rep", 12),
        ("new.admin@example.com", "admin", None),
    ]:
        body = {"email": email, "role": role}
        if hospital_id is not None:
            body["hospital_id"] = hospital_id
        response = create(client, admin, **body)
        assert response.status_code == 201, response.text
        assert response.json()["role"] == role and "password" not in response.text.lower()

        me = client.get("/api/auth/me", headers=login(client, email)).json()
        assert (me["role"], me["hospital_id"]) == (role, hospital_id)


def test_email_is_normalised_and_must_be_unique(client):
    admin = login(client, ADMIN)
    first = create(client, admin, email="Mixed.Case@Example.com", role="blood_bank_staff")
    assert first.status_code == 201 and first.json()["email"] == "mixed.case@example.com"

    duplicate = create(client, admin, email="mixed.case@example.com", role="admin")
    assert duplicate.status_code == 400 and "already exists" in duplicate.json()["detail"]


def test_role_and_hospital_rules(client):
    admin = login(client, ADMIN)
    # Donors sign up themselves; an admin cannot create one.
    assert create(client, admin, email="d@example.com", role="donor").status_code == 400
    # A hospital rep needs a hospital; nobody else may have one.
    assert create(client, admin, email="h@example.com", role="hospital_rep").status_code == 400
    assert create(client, admin, email="s@example.com", role="blood_bank_staff", hospital_id=3).status_code == 400
    assert create(client, admin, email="h@example.com", role="hospital_rep", hospital_id=0).status_code == 422
    assert create(client, admin, email="x@example.com", role="superuser").status_code == 422
    assert client.post("/api/admin/accounts", headers=admin, json={
        "email": "short@example.com", "password": "short", "role": "admin",
    }).status_code == 422


def test_only_admins_create_accounts(client):
    body = {"email": "nope@example.com", "role": "admin"}
    assert create(client, login(client, STAFF), **body).status_code == 403
    assert client.post("/api/admin/accounts", json={"password": PASSWORD, **body}).status_code == 401
