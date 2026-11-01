"""BLOOD-24: seed-demo smoke test for the role dashboards.

Seeds a fresh database with `python -m src.backend.cli seed-demo`, starts the real app
on it and, for every demo account, logs in and loads exactly the endpoints that role's
React dashboard calls (src/frontend/src/dashboards/*.jsx). If a dashboard would show an
error or an empty screen on the demo data, this test fails.
"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from src.backend import cli
from src.backend.config import AppSettings
from src.backend.database import create_all_tables, create_db_engine, create_session_factory
from src.backend.demo import DEMO_ACCOUNTS, DEMO_PASSWORD, DEMO_STOCK, seed_demo
from src.backend.inventory.service import SHELF_LIFE_DAYS
from src.backend.main import create_app

EMAIL = {role: email for email, role, _ in DEMO_ACCOUNTS}


@pytest.fixture
def database_url(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'demo.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("BBMS_CREATE_TABLES", "true")
    return url


@pytest.fixture
def client(database_url, capsys):
    assert cli.main(["seed-demo"]) == 0
    printed = capsys.readouterr().out
    assert all(email in printed for email in EMAIL.values())

    with TestClient(create_app(AppSettings(database_url=database_url))) as test_client:
        yield test_client


def login(client, role):
    response = client.post("/api/auth/login", json={"email": EMAIL[role], "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text
    assert response.json()["user"]["role"] == role
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def get_ok(client, path, headers):
    response = client.get(path, headers=headers)
    assert response.status_code == 200, f"{path}: {response.status_code} {response.text}"
    return response.json()


def test_staff_dashboard_has_stock_requests_and_drives(client):
    staff = login(client, "blood_bank_staff")

    bags = get_ok(client, "/api/inventory/bags", staff)
    seeded_stock = sum(
        1 for stock in DEMO_STOCK.values() for component, age in stock
        if age < SHELF_LIFE_DAYS[component]
    )
    # Plus the bag from the demo donor's donation 30 days ago (donor -> inventory link);
    # the one from 200 days ago has expired and the deferred one took no blood.
    assert len(bags) == seeded_stock + 1
    donor_bags = [b for b in bags if b["blood_group"] == "O-" and b["component"] == "Whole Blood"]
    assert len(donor_bags) == 2  # one from DEMO_STOCK, one from the donation
    assert {bag["blood_group"] for bag in bags} == set(DEMO_STOCK)
    assert all(date.fromisoformat(bag["expiry_date"]) > date.today() for bag in bags)

    pending = get_ok(client, "/api/requests/queue?status=PENDING", staff)
    approved = get_ok(client, "/api/requests/queue?status=APPROVED", staff)
    assert len(pending) == 4 and {r["urgency"] for r in pending} == {"emergency", "urgent", "routine"}
    assert len(approved) == 1

    drives = get_ok(client, "/api/drives", staff)
    assert len(drives) == 3
    for drive in drives:
        assert drive["slots"], drive
        assert all(0 <= s["booked_count"] <= s["capacity"] for s in drive["slots"])


def test_hospital_dashboard_lists_its_requests(client):
    hospital = login(client, "hospital_rep")
    requests = get_ok(client, "/api/requests", hospital)
    assert len(requests) == 5
    assert {r["status"] for r in requests} == {"PENDING", "APPROVED"}


def test_donor_dashboard_has_profile_history_and_drives(client):
    donor = login(client, "donor")

    profile = get_ok(client, "/api/donors/profile", donor)
    assert profile["blood_group"] == "O-"
    donations = get_ok(client, "/api/donors/me/donations", donor)
    assert len(donations) == 3
    get_ok(client, "/api/donors/me/eligibility", donor)
    assert get_ok(client, "/api/drives/bookings/me", donor) == []
    assert len(get_ok(client, "/api/drives", donor)) == 3


def test_admin_dashboard_loads(client):
    admin = login(client, "admin")
    assert get_ok(client, "/api/health", admin) == {"status": "ok"}
    upcoming = get_ok(client, "/api/drives", admin)
    assert all(date.fromisoformat(d["date"]) > date.today() for d in upcoming)
    assert all(date.fromisoformat(d["date"]) <= date.today() + timedelta(days=30) for d in upcoming)


def test_seed_demo_twice_adds_nothing(database_url):
    engine = create_db_engine(database_url)
    create_all_tables(engine)
    session_factory = create_session_factory(engine)
    with session_factory() as db:
        first = seed_demo(db)
    with session_factory() as db:
        assert seed_demo(db) == first

    with TestClient(create_app(AppSettings(database_url=database_url))) as client:
        staff = login(client, "blood_bank_staff")
        assert len(get_ok(client, "/api/drives", staff)) == 3
        assert len(get_ok(client, "/api/requests/queue?status=PENDING", staff)) == 4
    engine.dispose()
