"""Dashboard actions: the write calls the React dashboards make, through the wired app.

Each test signs in as more than one role and checks that an action taken in one
login is what the other logins see on their next refresh. Request bodies match
what the forms in src/frontend/src/dashboards/ send:

- staff: log a batch of bags, reject a request, dispatch from the APPROVED queue,
  schedule a drive, run the expiry check
- hospital: submit a request (required_by from `Date.toISOString()`, blank optional
  fields sent as "")
- donor: book a drive slot
- admin: schedule a drive, send reminders

Submit -> approve -> dispatch through inventory is covered in test_request_dispatch_flow.py.
"""
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.backend.auth.orm import Account
from src.backend.auth.security import hash_password
from src.backend.config import AppSettings
from src.backend.database import create_db_engine
from src.backend.main import create_app

PASSWORD = "ExamplePassword123!"
STAFF = "staff.ui@example.com"
ADMIN = "admin.ui@example.com"
HOSPITAL = "hospital.ui@example.com"
DONOR = "donor.ui@example.com"
SECOND_DONOR = "donor2.ui@example.com"
PROFILE = {
    "full_name": "Dashboard Donor",
    "blood_group": "O+",
    "date_of_birth": "1995-03-14",
    "weight_kg": "68",
    "phone": "9876500000",
}


class RecordingReminders:
    def __init__(self):
        self.sent = []

    def send_slot_reminder(self, email, drive_name, location, start_time):
        self.sent.append((email, drive_name))


@pytest.fixture
def reminders():
    return RecordingReminders()


@pytest.fixture
def client(tmp_path, reminders):
    settings = AppSettings(database_url=f"sqlite:///{tmp_path / 'bbms.db'}")
    app = create_app(settings, reminder_sender=reminders)
    with TestClient(app) as test_client:
        engine = create_db_engine(settings.database_url)
        with Session(engine) as db:
            db.add_all([
                Account(email=STAFF, password_hash=hash_password(PASSWORD), role="blood_bank_staff", is_verified=True),
                Account(email=ADMIN, password_hash=hash_password(PASSWORD), role="admin", is_verified=True),
                Account(email=HOSPITAL, password_hash=hash_password(PASSWORD), role="hospital_rep", hospital_id=3, is_verified=True),
                Account(email=DONOR, password_hash=hash_password(PASSWORD), role="donor", is_verified=True),
                Account(email=SECOND_DONOR, password_hash=hash_password(PASSWORD), role="donor", is_verified=True),
            ])
            db.commit()
        engine.dispose()
        yield test_client


def login(client, email):
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def donor_with_profile(client, email=DONOR):
    headers = login(client, email)
    response = client.post("/api/donors/profile", headers=headers, json=PROFILE)
    assert response.status_code == 201, response.text
    return headers


def drive_payload(day, first_hour=9, slots=3, capacity=10, name="Community drive"):
    """Back-to-back one-hour slots without a timezone, as DriveForm builds them."""
    return {
        "name": name,
        "location": "Main hall",
        "date": day.isoformat(),
        "slots": [
            {
                "start_time": f"{day.isoformat()}T{first_hour + i:02d}:00:00",
                "end_time": f"{day.isoformat()}T{first_hour + i + 1:02d}:00:00",
                "capacity": capacity,
            }
            for i in range(slots)
        ],
    }


def create_drive(client, headers, payload):
    response = client.post("/api/drives", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def log_bags(client, staff, count, blood_group="O+", component="RBC"):
    ids = []
    for _ in range(count):
        response = client.post("/api/inventory/bags", headers=staff, json={
            "blood_group": blood_group,
            "component": component,
            "collection_date": date.today().isoformat(),
        })
        assert response.status_code == 201, response.text
        ids.append(response.json()["unit_id"])
    return ids


def submit_from_form(client, hospital, **overrides):
    """The body RequestForm sends, including empty optional fields."""
    body = {
        "blood_group": "O+",
        "component": "RBC",
        "quantity": 1,
        "urgency": "routine",
        "required_by": None,
        "patient_reference": "",
        "notes": "",
        **overrides,
    }
    return client.post("/api/requests", headers=hospital, json=body)


def queue_ids(client, staff, status):
    response = client.get(f"/api/requests/queue?status={status}", headers=staff)
    assert response.status_code == 200, response.text
    return [r["id"] for r in response.json()]


# ---------- drives ----------

def test_drive_scheduled_by_staff_or_admin_is_visible_to_every_viewer(client):
    staff, admin = login(client, STAFF), login(client, ADMIN)
    donor = donor_with_profile(client)
    day = date.today() + timedelta(days=21)

    by_staff = create_drive(client, staff, drive_payload(day, slots=4, name="Staff drive"))
    by_admin = create_drive(client, admin, drive_payload(day, slots=1, name="Admin drive"))
    assert len(by_staff["slots"]) == 4
    assert by_staff["slots"][0]["booked_count"] == 0

    for headers in (staff, admin, donor):
        response = client.get("/api/drives", headers=headers)
        assert response.status_code == 200, response.text
        assert {by_staff["id"], by_admin["id"]} <= {d["id"] for d in response.json()}


def test_only_coordinators_can_schedule_drives(client):
    payload = drive_payload(date.today() + timedelta(days=21))
    for email in (HOSPITAL, DONOR):
        assert client.post("/api/drives", headers=login(client, email), json=payload).status_code == 403
    assert client.post("/api/drives", json=payload).status_code == 401
    # Hospitals don't see the drives list on their dashboard.
    assert client.get("/api/drives", headers=login(client, HOSPITAL)).status_code == 403


def test_drive_form_rules_are_enforced(client):
    staff = login(client, STAFF)
    day = date.today() + timedelta(days=21)

    no_slots = {**drive_payload(day), "slots": []}
    assert client.post("/api/drives", headers=staff, json=no_slots).status_code == 422

    wrong_day = drive_payload(day)
    wrong_day["slots"][0]["start_time"] = f"{(day + timedelta(days=1)).isoformat()}T09:00:00"
    wrong_day["slots"][0]["end_time"] = f"{(day + timedelta(days=1)).isoformat()}T10:00:00"
    response = client.post("/api/drives", headers=staff, json=wrong_day)
    assert response.status_code == 422
    assert "drive date" in response.text


# ---------- donor bookings ----------

def test_donor_booking_shows_up_for_staff_and_admin(client):
    staff, admin = login(client, STAFF), login(client, ADMIN)
    donor = donor_with_profile(client)
    drive = create_drive(client, staff, drive_payload(date.today() + timedelta(days=21)))
    slot = drive["slots"][1]

    booked = client.post(f"/api/drives/slots/{slot['id']}/book", headers=donor)
    assert booked.status_code == 201, booked.text

    mine = client.get("/api/drives/bookings/me", headers=donor).json()
    assert [(b["slot_id"], b["drive_id"]) for b in mine] == [(slot["id"], drive["id"])]
    for headers in (staff, admin):
        listed = next(d for d in client.get("/api/drives", headers=headers).json() if d["id"] == drive["id"])
        assert [s["booked_count"] for s in listed["slots"]] == [0, 1, 0]


def test_donor_gets_one_slot_per_drive(client):
    staff = login(client, STAFF)
    donor = donor_with_profile(client)
    drive = create_drive(client, staff, drive_payload(date.today() + timedelta(days=21)))
    first, second = drive["slots"][0]["id"], drive["slots"][1]["id"]

    assert client.post(f"/api/drives/slots/{first}/book", headers=donor).status_code == 201
    again = client.post(f"/api/drives/slots/{second}/book", headers=donor)
    assert again.status_code == 409
    assert again.json()["detail"] == "You already have a slot booked for this drive."


def test_full_slot_cannot_be_booked(client):
    staff = login(client, STAFF)
    drive = create_drive(client, staff, drive_payload(date.today() + timedelta(days=21), slots=1, capacity=1))
    slot_id = drive["slots"][0]["id"]

    assert client.post(f"/api/drives/slots/{slot_id}/book", headers=donor_with_profile(client)).status_code == 201
    late = client.post(f"/api/drives/slots/{slot_id}/book", headers=donor_with_profile(client, SECOND_DONOR))
    assert late.status_code == 409
    assert late.json()["detail"] == "This slot is fully booked."


def test_donor_without_profile_is_told_why_booking_failed(client):
    staff = login(client, STAFF)
    drive = create_drive(client, staff, drive_payload(date.today() + timedelta(days=21)))
    response = client.post(f"/api/drives/slots/{drive['slots'][0]['id']}/book", headers=login(client, DONOR))
    assert response.status_code == 409
    assert response.json()["detail"].startswith("You are not eligible to donate on the drive date")


def test_only_donors_can_book(client):
    drive = create_drive(client, login(client, STAFF), drive_payload(date.today() + timedelta(days=21)))
    path = f"/api/drives/slots/{drive['slots'][0]['id']}/book"
    for email in (STAFF, ADMIN, HOSPITAL):
        assert client.post(path, headers=login(client, email)).status_code == 403


def test_admin_sends_reminders_for_slots_starting_soon(client, reminders):
    admin = login(client, ADMIN)
    donor = donor_with_profile(client)
    # A slot a couple of hours from now (naive times are read as UTC by the backend).
    start = (datetime.now(timezone.utc) + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0, tzinfo=None)
    soon = {
        "name": "Today's drive",
        "location": "Lobby",
        "date": start.date().isoformat(),
        "slots": [{"start_time": start.isoformat(), "end_time": (start + timedelta(minutes=30)).isoformat(), "capacity": 5}],
    }
    drive = create_drive(client, admin, soon)
    # The demo-style donor has never donated, so they can book today.
    assert client.post(f"/api/drives/slots/{drive['slots'][0]['id']}/book", headers=donor).status_code == 201

    response = client.post("/api/drives/reminders/send", headers=admin)
    assert response.status_code == 200, response.text
    assert response.json()["reminders_sent"] == 1
    assert reminders.sent == [(DONOR, "Today's drive")]
    # Already reminded: a second run sends nothing.
    assert client.post("/api/drives/reminders/send", headers=admin).json()["reminders_sent"] == 0
    assert client.post("/api/drives/reminders/send", headers=login(client, HOSPITAL)).status_code == 403


# ---------- stock ----------

def test_logging_a_batch_of_bags_adds_each_one_to_stock(client):
    staff = login(client, STAFF)
    before = len(client.get("/api/inventory/bags", headers=staff).json())

    ids = log_bags(client, staff, 5, blood_group="AB-", component="Plasma")

    stock = client.get("/api/inventory/bags", headers=staff).json()
    assert len(stock) == before + 5
    assert len(set(ids)) == 5  # every bag gets its own unit ID
    new = [b for b in stock if b["unit_id"] in ids]
    assert {(b["blood_group"], b["component"], b["status"]) for b in new} == {("AB-", "Plasma", "AVAILABLE")}


def test_bags_collected_in_the_future_are_refused(client):
    staff = login(client, STAFF)
    response = client.post("/api/inventory/bags", headers=staff, json={
        "blood_group": "O+",
        "component": "RBC",
        "collection_date": (date.today() + timedelta(days=1)).isoformat(),
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Collection date cannot be in the future"


def test_expiry_check_from_the_dashboard(client):
    staff = login(client, STAFF)
    response = client.post("/api/inventory/expire", headers=staff)
    assert response.status_code == 200, response.text
    assert response.json() == {"expired_count": 0}
    assert client.post("/api/inventory/expire", headers=login(client, HOSPITAL)).status_code == 403


# ---------- hospital requests ----------

def test_request_from_the_form_reaches_the_staff_queue(client):
    staff, hospital = login(client, STAFF), login(client, HOSPITAL)
    needed_by = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    response = submit_from_form(client, hospital, quantity=2, urgency="emergency", required_by=needed_by,
                                patient_reference="", notes="Theatre 4")
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["status"] == "PENDING"
    assert created["hospital_id"] == 3
    assert created["patient_reference"] is None  # blank field stored as empty
    assert created["notes"] == "Theatre 4"

    queue = client.get("/api/requests/queue?status=PENDING", headers=staff).json()
    assert [(r["id"], r["urgency"], r["quantity"]) for r in queue] == [(created["id"], "emergency", 2)]


def test_request_form_validation(client):
    hospital = login(client, HOSPITAL)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    assert submit_from_form(client, hospital, required_by=past).status_code == 422
    assert submit_from_form(client, hospital, quantity=11).status_code == 422  # MAX_UNITS_PER_REQUEST
    assert submit_from_form(client, hospital, quantity=0).status_code == 422


def test_rejected_request_leaves_the_queue_and_hospital_sees_it(client):
    staff, hospital = login(client, STAFF), login(client, HOSPITAL)
    request_id = submit_from_form(client, hospital).json()["id"]

    assert client.post(f"/api/requests/{request_id}/reject", headers=staff, json={"reason": ""}).status_code == 422
    response = client.post(f"/api/requests/{request_id}/reject", headers=staff, json={"reason": "Wrong group requested"})
    assert response.status_code == 200, response.text

    assert queue_ids(client, staff, "PENDING") == []
    assert client.get(f"/api/requests/{request_id}", headers=hospital).json()["status"] == "REJECTED"
    history = client.get(f"/api/requests/{request_id}/history", headers=staff).json()
    assert history[-1]["action"] == "REJECTED"
    assert history[-1]["note"] == "Wrong group requested"
    # A rejected request can't be approved afterwards.
    assert client.post(f"/api/requests/{request_id}/approve", headers=staff).status_code == 409


def test_request_moves_between_the_staff_tables(client):
    """Pending table -> Ready to dispatch table -> gone, while the hospital's view follows."""
    staff, hospital = login(client, STAFF), login(client, HOSPITAL)
    log_bags(client, staff, 2)
    request_id = submit_from_form(client, hospital, quantity=2).json()["id"]
    hospital_status = lambda: client.get("/api/requests", headers=hospital).json()[0]["status"]  # noqa: E731

    assert (queue_ids(client, staff, "PENDING"), queue_ids(client, staff, "APPROVED")) == ([request_id], [])
    assert hospital_status() == "PENDING"

    assert client.post(f"/api/requests/{request_id}/approve", headers=staff).status_code == 200
    assert (queue_ids(client, staff, "PENDING"), queue_ids(client, staff, "APPROVED")) == ([], [request_id])
    assert hospital_status() == "APPROVED"
    assert client.get("/api/inventory/bags", headers=staff).json() == []  # allocated units leave stock

    assert client.post(f"/api/requests/{request_id}/dispatch", headers=staff).status_code == 200
    assert (queue_ids(client, staff, "PENDING"), queue_ids(client, staff, "APPROVED")) == ([], [])
    assert hospital_status() == "DISPATCHED"
