"""BLOOD-23: Hospital Request <-> Inventory integration through the fully wired app.

Boots the real `create_app()` from src/backend/main.py (every router, the shared
database and InventoryCrossMatch) on a temporary SQLite file, then drives the
submit -> approve -> dispatch flow over HTTP the way the frontend does.

Test plan traceability: TC-HR-01 (cross-match allocates compatible units),
TC-HR-02 (insufficient stock is refused), TC-Inv-xx (no negative stock / no double
allocation), TC-Auth-xx (RBAC between hospital and staff roles).
"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.backend.auth.orm import Account
from src.backend.auth.security import hash_password
from src.backend.config import AppSettings
from src.backend.database import create_db_engine
from src.backend.main import create_app

PASSWORD = "ExamplePassword123!"
STAFF = "staff@example.com"
HOSPITAL = "hospital@example.com"


@pytest.fixture
def client(tmp_path):
    settings = AppSettings(database_url=f"sqlite:///{tmp_path / 'bbms.db'}")
    app = create_app(settings)
    with TestClient(app) as test_client:  # startup creates every table
        engine = create_db_engine(settings.database_url)
        with Session(engine) as db:
            db.add_all([
                Account(email=STAFF, password_hash=hash_password(PASSWORD),
                        role="blood_bank_staff", is_verified=True),
                Account(email=HOSPITAL, password_hash=hash_password(PASSWORD),
                        role="hospital_rep", hospital_id=7, is_verified=True),
            ])
            db.commit()
        engine.dispose()
        yield test_client


def login(client, email):
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def log_bag(client, staff, blood_group, component="RBC", days_ago=1):
    response = client.post("/api/inventory/bags", headers=staff, json={
        "blood_group": blood_group,
        "component": component,
        "collection_date": (date.today() - timedelta(days=days_ago)).isoformat(),
    })
    assert response.status_code == 201, response.text
    return response.json()["unit_id"]


def submit(client, hospital, blood_group, quantity, component="RBC"):
    response = client.post("/api/requests", headers=hospital, json={
        "blood_group": blood_group,
        "component": component,
        "quantity": quantity,
        "urgency": "urgent",
    })
    assert response.status_code == 201, response.text
    return response.json()["id"]


def bag_status(client, staff, unit_id):
    response = client.get(f"/api/inventory/bags/{unit_id}", headers=staff)
    assert response.status_code == 200, response.text
    return response.json()["status"]


def available_ids(client, staff):
    response = client.get("/api/inventory/bags", headers=staff)
    assert response.status_code == 200, response.text
    return {bag["unit_id"] for bag in response.json()}


def test_health_endpoint(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_submit_approve_dispatch_moves_units_through_inventory(client):
    """TC-HR-01: exact group is preferred, units are allocated then dispatched."""
    staff, hospital = login(client, STAFF), login(client, HOSPITAL)
    a_pos = [log_bag(client, staff, "A+"), log_bag(client, staff, "A+")]
    o_neg = log_bag(client, staff, "O-")

    request_id = submit(client, hospital, "A+", 2)
    queue = client.get("/api/requests/queue", headers=staff).json()
    assert [r["id"] for r in queue] == [request_id]

    preview = client.get(f"/api/requests/{request_id}/matches", headers=staff).json()
    assert preview["sufficient"] is True
    assert {u["unit_id"] for u in preview["units"]} == set(a_pos)  # O- is saved for others

    approved = client.post(f"/api/requests/{request_id}/approve", headers=staff)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"
    units = client.get(f"/api/requests/{request_id}/units", headers=staff).json()["unit_ids"]
    assert set(units) == set(a_pos)
    assert all(bag_status(client, staff, u) == "ALLOCATED" for u in a_pos)
    assert available_ids(client, staff) == {o_neg}

    dispatched = client.post(f"/api/requests/{request_id}/dispatch", headers=staff)
    assert dispatched.status_code == 200, dispatched.text
    assert dispatched.json()["status"] == "DISPATCHED"
    assert all(bag_status(client, staff, u) == "DISPATCHED" for u in a_pos)
    assert bag_status(client, staff, o_neg) == "AVAILABLE"

    # The hospital sees its own request as dispatched.
    mine = client.get(f"/api/requests/{request_id}", headers=hospital).json()
    assert mine["status"] == "DISPATCHED"
    history = client.get(f"/api/requests/{request_id}/history", headers=staff).json()
    assert [e["action"] for e in history][-2:] == ["APPROVED", "DISPATCHED"]


def test_approve_with_insufficient_stock_is_refused(client):
    """TC-HR-02: no partial allocation, nothing leaves stock, request stays pending."""
    staff, hospital = login(client, STAFF), login(client, HOSPITAL)
    only_bag = log_bag(client, staff, "B+")
    request_id = submit(client, hospital, "B+", 3)

    response = client.post(f"/api/requests/{request_id}/approve", headers=staff)
    assert response.status_code == 409
    assert response.json()["detail"] == {"error": "insufficient_stock", "requested": 3, "available": 1}
    assert client.get(f"/api/requests/{request_id}", headers=hospital).json()["status"] == "PENDING"
    assert available_ids(client, staff) == {only_bag}


def test_a_unit_is_never_allocated_to_two_requests(client):
    """No double allocation: the second request cannot take an already allocated bag."""
    staff, hospital = login(client, STAFF), login(client, HOSPITAL)
    log_bag(client, staff, "AB+")
    first = submit(client, hospital, "AB+", 1)
    second = submit(client, hospital, "AB+", 1)

    assert client.post(f"/api/requests/{first}/approve", headers=staff).status_code == 200
    response = client.post(f"/api/requests/{second}/approve", headers=staff)
    assert response.status_code == 409
    assert response.json()["detail"]["available"] == 0


def test_incompatible_and_expired_units_are_not_matched(client):
    """Cross-match ignores incompatible blood groups and expired bags."""
    staff, hospital = login(client, STAFF), login(client, HOSPITAL)
    log_bag(client, staff, "A+")  # A+ cannot go to an O+ patient
    expired = log_bag(client, staff, "O+", component="Platelets", days_ago=10)  # 5-day shelf life
    assert bag_status(client, staff, expired) == "EXPIRED"

    rbc = submit(client, hospital, "O+", 1)
    platelets = submit(client, hospital, "O+", 1, component="Platelets")
    for request_id in (rbc, platelets):
        preview = client.get(f"/api/requests/{request_id}/matches", headers=staff).json()
        assert preview["sufficient"] is False
        assert preview["units"] == []


def test_roles_are_enforced_across_modules(client):
    """RBAC: hospitals cannot touch inventory or approve; staff cannot submit requests."""
    staff, hospital = login(client, STAFF), login(client, HOSPITAL)
    bag = {"blood_group": "O+", "component": "RBC", "collection_date": date.today().isoformat()}

    assert client.post("/api/inventory/bags", headers=hospital, json=bag).status_code == 403
    assert client.get("/api/inventory/bags", headers=hospital).status_code == 403
    request_id = submit(client, hospital, "O+", 1)
    assert client.post(f"/api/requests/{request_id}/approve", headers=hospital).status_code == 403
    assert client.post("/api/requests", headers=staff, json={
        "blood_group": "O+", "component": "RBC", "quantity": 1,
    }).status_code == 403
    assert client.get("/api/requests/queue").status_code == 401


def test_dispatch_requires_approval_first(client):
    staff, hospital = login(client, STAFF), login(client, HOSPITAL)
    log_bag(client, staff, "O+")
    request_id = submit(client, hospital, "O+", 1)

    response = client.post(f"/api/requests/{request_id}/dispatch", headers=staff)
    assert response.status_code == 409
    assert client.get(f"/api/requests/{request_id}", headers=hospital).json()["status"] == "PENDING"
