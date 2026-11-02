from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.backend.auth.orm import Account
from src.backend.auth.security import hash_password
from src.backend.config import AppSettings
from src.backend.database import create_db_engine
from src.backend.main import create_app


@pytest.fixture
def client(tmp_path):
    settings = AppSettings(database_url=f"sqlite:///{tmp_path / 'bbms.db'}")
    app = create_app(settings)
    with TestClient(app) as test_client:
        engine = create_db_engine(settings.database_url)
        with Session(engine) as db:
            db.add_all([
                Account(email="staff25@example.com", password_hash=hash_password("ExamplePassword123!"), role="blood_bank_staff", is_verified=True),
                Account(email="hospital25@example.com", password_hash=hash_password("ExamplePassword123!"), role="hospital_rep", hospital_id=7, is_verified=True),
            ])
            db.commit()
        engine.dispose()
        yield test_client


def login(client, email):
    response = client.post("/api/auth/login", json={"email": email, "password": "ExamplePassword123!"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_staff_can_get_low_stock_alerts(client):
    staff = login(client, "staff25@example.com")
    response = client.get("/api/inventory/low-stock?threshold=1", headers=staff)
    assert response.status_code == 200, response.text
    assert any(x["blood_group"] == "O+" and x["component"] == "RBC" and x["level"] == "OUT_OF_STOCK" for x in response.json())
    created = client.post("/api/inventory/bags", headers=staff, json={"blood_group": "O+", "component": "RBC", "collection_date": date.today().isoformat()})
    assert created.status_code == 201, created.text
    updated = client.get("/api/inventory/low-stock?threshold=1", headers=staff)
    assert any(x["blood_group"] == "O+" and x["component"] == "RBC" and x["available_units"] == 1 and x["level"] == "LOW_STOCK" for x in updated.json())
    assert not any(x["blood_group"] == "O+" and x["component"] == "RBC" for x in client.get("/api/inventory/low-stock?threshold=0", headers=staff).json())


def test_hospital_cannot_view_alerts(client):
    hospital = login(client, "hospital25@example.com")
    assert client.get("/api/inventory/low-stock", headers=hospital).status_code == 403
    assert client.get("/api/inventory/low-stock").status_code == 401


def test_invalid_threshold_returns_422(client):
    staff = login(client, "staff25@example.com")
    assert client.get("/api/inventory/low-stock?threshold=-1", headers=staff).status_code == 422
