"""BLOOD-9: donor profile API access and validation."""

from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.backend.auth.dependencies import create_auth_dependencies
from src.backend.auth.orm import Account, AuthBase
from src.backend.auth.routes import create_router
from src.backend.auth.security import hash_password
from src.backend.donor.models import Base, DonorProfile
from src.backend.donor.profile_routes import create_profile_router


PASSWORD = "ExamplePassword123!"
PROFILE = {
    "full_name": "Test Donor",
    "blood_group": "O+",
    "date_of_birth": "2002-05-12",
    "weight_kg": "52.5",
    "phone": "9876543210",
}


@pytest.fixture
def setup_api():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(engine)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        for email, role in (
            ("donor1@example.com", "donor"),
            ("donor2@example.com", "donor"),
            ("staff@example.com", "blood_bank_staff"),
        ):
            db.add(Account(
                email=email,
                password_hash=hash_password(PASSWORD),
                role=role,
                is_verified=True,
            ))
        db.commit()

    def get_session():
        with Session(engine) as db:
            yield db

    get_current_user, require_role = create_auth_dependencies(get_session)
    app = FastAPI()
    app.include_router(create_router(get_session, get_current_user))
    app.include_router(create_profile_router(get_session, require_role))

    with TestClient(app) as client:
        yield client, engine

    engine.dispose()


def headers_for(client, email):
    response = client.post("/api/auth/login", json={
        "email": email, "password": PASSWORD,
    })
    assert response.status_code == 200, response.text
    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }, response.json()["user"]["id"]


def test_donor_creates_and_reads_only_own_profile(setup_api):
    client, engine = setup_api
    donor1_headers, donor1_id = headers_for(client, "donor1@example.com")
    donor2_headers, donor2_id = headers_for(client, "donor2@example.com")

    assert client.get(
        "/api/donors/profile", headers=donor2_headers
    ).status_code == 404

    payload = {**PROFILE, "donor_id": donor2_id}
    created = client.post(
        "/api/donors/profile", headers=donor1_headers, json=payload
    )
    assert created.status_code == 201, created.text
    assert created.json()["donor_id"] == donor1_id
    assert created.json()["age"] == (
        date.today().year - 2002
        - ((date.today().month, date.today().day) < (5, 12))
    )

    own = client.get("/api/donors/profile", headers=donor1_headers)
    assert own.status_code == 200
    assert own.json()["full_name"] == "Test Donor"

    other = client.get("/api/donors/profile", headers=donor2_headers)
    assert other.status_code == 404

    with Session(engine) as db:
        assert db.get(DonorProfile, donor1_id) is not None
        assert db.get(DonorProfile, donor2_id) is None


def test_staff_and_unauthenticated_callers_are_denied(setup_api):
    client, _ = setup_api
    staff_headers, _ = headers_for(client, "staff@example.com")

    assert client.post(
        "/api/donors/profile", headers=staff_headers, json=PROFILE
    ).status_code == 403
    assert client.get(
        "/api/donors/profile", headers=staff_headers
    ).status_code == 403
    assert client.post(
        "/api/donors/profile", json=PROFILE
    ).status_code == 401


def test_required_fields_and_duplicate_profile(setup_api):
    client, _ = setup_api
    donor_headers, _ = headers_for(client, "donor1@example.com")

    missing_phone = {key: value for key, value in PROFILE.items()
                     if key != "phone"}
    assert client.post(
        "/api/donors/profile", headers=donor_headers, json=missing_phone
    ).status_code == 422

    blank_name = {**PROFILE, "full_name": "   "}
    assert client.post(
        "/api/donors/profile", headers=donor_headers, json=blank_name
    ).status_code == 400

    assert client.post(
        "/api/donors/profile", headers=donor_headers, json=PROFILE
    ).status_code == 201
    assert client.post(
        "/api/donors/profile", headers=donor_headers, json=PROFILE
    ).status_code == 400
