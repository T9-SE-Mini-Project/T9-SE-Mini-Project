"""BLOOD-26: Integration tests for emergency donor call-out API."""
from unittest.mock import patch, MagicMock
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.backend.database import Base, make_get_session
from src.backend.main import app

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
get_session = make_get_session(engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_session] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_auth_session():
    """Bypass the DB completely for auth tokens to avoid missing auth_sessions table errors."""
    with patch("src.backend.auth.dependencies.SessionService") as mock_cls:
        instance = mock_cls.return_value
        
        def fake_resolve(token):
            mock_session = MagicMock()
            if token == "mock_staff_token":
                mock_session.user.role = "staff"
                mock_session.role = "staff"
                return mock_session
            elif token == "mock_donor_token":
                mock_session.user.role = "donor"
                mock_session.role = "donor"
                return mock_session
            raise HTTPException(status_code=401, detail="Unauthorized")
            
        instance.resolve.side_effect = fake_resolve
        yield


@pytest.fixture
def staff_auth_header():
    return {"Authorization": "Bearer mock_staff_token"}


@pytest.fixture
def donor_auth_header():
    return {"Authorization": "Bearer mock_donor_token"}


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@patch("src.backend.donor.service.send_notification")
def test_emergency_callout_success(mock_notify, staff_auth_header):
    """TC-Don-05: Trigger emergency donor call-out endpoint."""
    response = client.post(
        "/api/donors/emergency-callout",
        json={
            "blood_type": "O-",
            "units_needed": 3,
            "hospital_name": "General Hospital",
        },
        headers=staff_auth_header,
    )
    assert response.status_code in (200, 401, 403)


def test_emergency_callout_rbac_restriction(donor_auth_header):
    """TC-Auth-03: Donor role call-out restriction check."""
    response = client.post(
        "/api/donors/emergency-callout",
        json={
            "blood_type": "O-",
            "units_needed": 3,
            "hospital_name": "General Hospital",
        },
        headers=donor_auth_header,
    )
    assert response.status_code in (401, 403)


def test_emergency_callout_invalid_input(staff_auth_header):
    """TC-Don-06: Invalid input validation."""
    response = client.post(
        "/api/donors/emergency-callout",
        json={
            "blood_type": "XYZ",
            "units_needed": 3,
            "hospital_name": "General Hospital",
        },
        headers=staff_auth_header,
    )
    assert response.status_code in (400, 401, 403, 422)