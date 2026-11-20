"""System validation: end-to-end scenarios against a running BBMS server.

Each test is one system test case (ST-xx) from docs/Test_Cases.md and checks the
acceptance criterion of the SRS requirement named in its docstring. The harness is in
conftest.py. Results are reported in docs/System_Validation_Report.md.
"""
from __future__ import annotations

import statistics
import threading
import time
from datetime import date, datetime, timedelta, timezone

from .conftest import ADMIN_EMAIL, PASSWORD

PROFILE = {
    "full_name": "System Test Donor",
    "blood_group": "O+",
    "date_of_birth": "1995-03-14",
    "weight_kg": "68",
    "phone": "9876500000",
}


def drive_body(name: str, start: datetime, capacity: int = 10) -> dict:
    return {
        "name": name,
        "location": "PES University, Bengaluru",
        "date": start.date().isoformat(),
        "slots": [{
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=1)).isoformat(),
            "capacity": capacity,
        }],
    }


def test_st01_server_is_up_and_serves_api_docs(bbms):
    """ST-01 / BBS-NF-002: the running server answers health checks and serves its API docs."""
    assert bbms.http.get("/api/health").json() == {"status": "ok"}
    assert bbms.http.get("/docs").status_code == 200
    paths = bbms.http.get("/openapi.json").json()["paths"]
    for path in ("/api/auth/login", "/api/donors/profile", "/api/inventory/bags", "/api/requests", "/api/drives"):
        assert path in paths


def test_st02_four_roles_log_in_and_get_their_own_role(bbms):
    """ST-02 / BBS-F-001, AC-001: Donor, Hospital Rep, Staff and Admin log in; each is told its own role."""
    sessions = {
        "admin": bbms.admin(),
        "blood_bank_staff": bbms.staff(),
        "hospital_rep": bbms.hospital(hospital_id=4),
        "donor": bbms.new_donor()[1],
    }
    for role, headers in sessions.items():
        me = bbms.http.get("/api/auth/me", headers=headers).json()
        assert me["role"] == role
    assert bbms.http.get("/api/auth/me", headers=sessions["hospital_rep"]).json()["hospital_id"] == 4

    wrong = bbms.http.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "not-the-password"})
    assert wrong.status_code == 401


def test_st03_signup_completes_only_after_the_correct_otp(bbms):
    """ST-03 / BBS-F-002, AC-002: an unverified donor cannot log in; a wrong code is refused."""
    email = "new.donor@example.com"
    credentials = {"email": email, "password": PASSWORD}
    assert bbms.http.post("/api/auth/signup", json=credentials).status_code == 202
    code = bbms.otp_for(email)

    assert bbms.http.post("/api/auth/login", json=credentials).status_code == 401
    wrong = f"{(int(code) + 1) % 1_000_000:06d}"
    assert bbms.http.post("/api/auth/signup/verify", json={"email": email, "code": wrong}).status_code == 400
    assert bbms.http.post("/api/auth/login", json=credentials).status_code == 401

    assert bbms.http.post("/api/auth/signup/verify", json={"email": email, "code": code}).status_code == 200
    assert bbms.http.post("/api/auth/login", json=credentials).status_code == 200
    # The same email cannot sign up twice.
    assert bbms.http.post("/api/auth/signup", json=credentials).status_code == 409


def test_st04_account_locks_after_five_wrong_passwords(bbms):
    """ST-04 / BBS-F-003, AC-003: after 5 wrong attempts even the right password is refused."""
    email, _ = bbms.new_account("blood_bank_staff")
    for _ in range(5):
        response = bbms.http.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
        assert response.status_code == 401
    locked = bbms.http.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert locked.status_code == 401

    (locked_until,) = bbms.sql("SELECT locked_until FROM auth_users WHERE email = ?", (email,))[0]
    remaining = locked_until - time.time()
    assert 29 * 60 < remaining <= 30 * 60  # locked for 30 minutes

    # Other accounts are not affected.
    assert bbms.http.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}).status_code == 200


def test_st05_donor_profile_needs_every_required_field(bbms):
    """ST-05 / BBS-F-010, AC-010: the profile is not saved while a required field is missing or empty."""
    _, donor = bbms.new_donor()
    for field in PROFILE:
        missing = {key: value for key, value in PROFILE.items() if key != field}
        assert bbms.http.post("/api/donors/profile", headers=donor, json=missing).status_code == 422
    empty_name = {**PROFILE, "full_name": ""}
    assert bbms.http.post("/api/donors/profile", headers=donor, json=empty_name).status_code == 422
    assert bbms.http.get("/api/donors/profile", headers=donor).status_code == 404

    created = bbms.http.post("/api/donors/profile", headers=donor, json=PROFILE)
    assert created.status_code == 201
    saved = bbms.http.get("/api/donors/profile", headers=donor).json()
    assert saved["blood_group"] == "O+" and saved["full_name"] == PROFILE["full_name"]
    assert float(saved["weight_kg"]) == 68.0


def test_st06_eligibility_rules_and_donation_history(bbms):
    """ST-06 / BBS-F-011, BBS-F-012, AC-011, AC-012: a donation 30 days ago makes the donor
    not yet eligible, shows in their history, and adds a Whole Blood bag to stock."""
    staff = bbms.staff()
    _, donor = bbms.new_donor(PROFILE)
    donor_id = bbms.user_id(donor)

    before = bbms.http.get("/api/donors/me/eligibility", headers=donor).json()
    assert before["eligible"] is True

    donated_on = date.today() - timedelta(days=30)
    recorded = bbms.http.post(f"/api/donors/{donor_id}/donations", headers=staff, json={
        "donation_date": donated_on.isoformat(), "quantity_ml": 450,
    })
    assert recorded.status_code == 201, recorded.text
    unit_id = recorded.json()["unit_id"]

    after = bbms.http.get("/api/donors/me/eligibility", headers=donor).json()
    assert after["eligible"] is False
    assert after["next_eligible_date"] == (donated_on + timedelta(days=56)).isoformat()

    history = bbms.http.get("/api/donors/me/donations", headers=donor).json()
    assert [(d["donation_date"], d["quantity_ml"], d["status"]) for d in history] == [
        (donated_on.isoformat(), 450, "COMPLETED"),
    ]
    bag = bbms.http.get(f"/api/inventory/bags/{unit_id}", headers=staff).json()
    assert (bag["blood_group"], bag["component"]) == ("O+", "Whole Blood")

    # A second completed donation inside the 56-day gap is refused.
    again = bbms.http.post(f"/api/donors/{donor_id}/donations", headers=staff, json={
        "donation_date": date.today().isoformat(), "quantity_ml": 450,
    })
    assert again.status_code == 409

    # Weight and age rules.
    _, light = bbms.new_donor({**PROFILE, "weight_kg": "44"})
    assert bbms.http.get("/api/donors/me/eligibility", headers=light).json()["eligible"] is False
    minor_dob = date.today().replace(year=date.today().year - 17).isoformat()
    _, minor = bbms.new_donor({**PROFILE, "date_of_birth": minor_dob})
    assert bbms.http.get("/api/donors/me/eligibility", headers=minor).json()["eligible"] is False


def test_st07_bags_get_unique_ids_and_expiry_by_component(bbms):
    """ST-07 / BBS-F-020, BBS-F-021, AC-020, AC-021: every bag has a unique, searchable ID and
    its expiry date is filled in from the component type."""
    staff = bbms.staff()
    shelf_life = {"Whole Blood": 35, "RBC": 42, "Platelets": 5, "Plasma": 365}
    collected = date.today() - timedelta(days=1)
    bags = [bbms.log_bag(staff, "A+", component) for component in shelf_life for _ in range(3)]

    assert len({bag["unit_id"] for bag in bags}) == len(bags)
    for bag in bags:
        assert bag["expiry_date"] == (collected + timedelta(days=shelf_life[bag["component"]])).isoformat()
        found = bbms.http.get(f"/api/inventory/bags/{bag['unit_id']}", headers=staff)
        assert found.status_code == 200 and found.json() == bag
    assert bbms.http.get("/api/inventory/bags/BBU-DOES-NOT-EXIST", headers=staff).status_code == 404


def test_st08_expired_units_leave_available_stock_with_an_audit_entry(bbms):
    """ST-08 / BBS-F-022, BBS-SR-004, AC-022: an expired unit is not in available stock, and
    marking it expired is logged with user and timestamp."""
    staff = bbms.staff()
    fresh = bbms.log_bag(staff, "B+", "Platelets", days_ago=1)
    already_expired = bbms.log_bag(staff, "B+", "Platelets", days_ago=10)  # 5-day shelf life
    assert already_expired["status"] == "EXPIRED"

    # A unit whose expiry date passes while it sits in stock (time simulated in the database).
    ageing = bbms.log_bag(staff, "B+", "RBC", days_ago=2)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    bbms.sql("UPDATE blood_bags SET expiry_date = ? WHERE unit_id = ?", (yesterday, ageing["unit_id"]))

    available = {bag["unit_id"] for bag in bbms.http.get("/api/inventory/bags", headers=staff).json()}
    assert available == {fresh["unit_id"]}

    run = bbms.http.post("/api/inventory/expire", headers=staff)
    assert run.status_code == 200 and run.json() == {"expired_count": 1}
    assert bbms.http.get(f"/api/inventory/bags/{ageing['unit_id']}", headers=staff).json()["status"] == "EXPIRED"

    events = bbms.sql("SELECT action, actor_id, created_at FROM inventory_events WHERE unit_id = ?", (ageing["unit_id"],))
    assert len(events) == 1
    action, actor_id, created_at = events[0]
    assert action == "EXPIRED" and actor_id == bbms.user_id(staff) and created_at


def test_st09_hospital_request_is_matched_approved_and_dispatched(bbms):
    """ST-09 / BBS-F-030, BBS-F-031, BBS-F-032, BBS-SR-004, AC-030..032: a submitted request
    shows in the staff queue, only compatible units are suggested (never B- for A+), and
    approving then dispatching moves it to 'Dispatched' with an audit trail."""
    staff, hospital = bbms.staff(), bbms.hospital(hospital_id=7)
    a_pos = bbms.log_bag(staff, "A+")["unit_id"]
    o_neg = bbms.log_bag(staff, "O-")["unit_id"]
    b_neg = bbms.log_bag(staff, "B-")["unit_id"]

    request_id = bbms.submit_request(hospital, "A+", 2)
    queue = bbms.http.get("/api/requests/queue", headers=staff).json()
    assert [r["id"] for r in queue] == [request_id]

    preview = bbms.http.get(f"/api/requests/{request_id}/matches", headers=staff).json()
    suggested = {unit["unit_id"] for unit in preview["units"]}
    assert preview["sufficient"] is True
    assert suggested == {a_pos, o_neg} and b_neg not in suggested

    approved = bbms.http.post(f"/api/requests/{request_id}/approve", headers=staff)
    assert approved.status_code == 200 and approved.json()["status"] == "APPROVED"
    dispatched = bbms.http.post(f"/api/requests/{request_id}/dispatch", headers=staff)
    assert dispatched.status_code == 200 and dispatched.json()["status"] == "DISPATCHED"

    assert bbms.http.get(f"/api/requests/{request_id}", headers=hospital).json()["status"] == "DISPATCHED"
    for unit_id in (a_pos, o_neg):
        assert bbms.http.get(f"/api/inventory/bags/{unit_id}", headers=staff).json()["status"] == "DISPATCHED"
    available = {bag["unit_id"] for bag in bbms.http.get("/api/inventory/bags", headers=staff).json()}
    assert available == {b_neg}

    history = bbms.http.get(f"/api/requests/{request_id}/history", headers=staff).json()
    assert [event["action"] for event in history][-2:] == ["APPROVED", "DISPATCHED"]
    staff_id = bbms.user_id(staff)
    assert all(event["actor_id"] == staff_id and event["created_at"] for event in history[-2:])

    # Not enough compatible stock: refused, nothing is taken.
    short = bbms.submit_request(hospital, "A+", 2)
    refused = bbms.http.post(f"/api/requests/{short}/approve", headers=staff)
    assert refused.status_code == 409
    assert bbms.http.get(f"/api/requests/{short}", headers=hospital).json()["status"] == "PENDING"


def test_st10_drive_needs_a_slot_and_a_full_slot_cannot_be_booked(bbms):
    """ST-10 / BBS-F-040, BBS-F-041, AC-040, AC-041: a drive without slots is refused; donors
    see upcoming drives and book; a full slot refuses the next donor."""
    staff = bbms.staff()
    start = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=7)

    no_slots = {**drive_body("Empty Drive", start), "slots": []}
    assert bbms.http.post("/api/drives", headers=staff, json=no_slots).status_code == 422

    created = bbms.http.post("/api/drives", headers=staff, json=drive_body("Campus Drive", start, capacity=1))
    assert created.status_code == 201, created.text
    slot_id = created.json()["slots"][0]["id"]

    _, first = bbms.new_donor(PROFILE)
    _, second = bbms.new_donor(PROFILE)
    listed = bbms.http.get("/api/drives", headers=first).json()
    assert [drive["name"] for drive in listed] == ["Campus Drive"]

    booked = bbms.http.post(f"/api/drives/slots/{slot_id}/book", headers=first)
    assert booked.status_code == 201, booked.text
    full = bbms.http.post(f"/api/drives/slots/{slot_id}/book", headers=second)
    assert full.status_code == 409 and "fully booked" in full.json()["detail"]

    mine = bbms.http.get("/api/drives/bookings/me", headers=first).json()
    assert [booking["slot_id"] for booking in mine] == [slot_id]
    assert bbms.http.get("/api/drives/bookings/me", headers=second).json() == []
    assert bbms.http.get("/api/drives", headers=staff).json()[0]["slots"][0]["booked_count"] == 1


def test_st11_reminder_goes_out_once_before_the_booked_slot(bbms):
    """ST-11 / BBS-F-042, AC-042: a donor booked on a slot in the next 24 hours is reminded
    once; a booking further away is not reminded yet."""
    admin = bbms.admin()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    soon = bbms.http.post("/api/drives", headers=admin, json=drive_body("Tomorrow Drive", now + timedelta(hours=3))).json()
    later = bbms.http.post("/api/drives", headers=admin, json=drive_body("Next Week Drive", now + timedelta(days=7))).json()

    _, donor = bbms.new_donor(PROFILE)
    soon_booking = bbms.http.post(f"/api/drives/slots/{soon['slots'][0]['id']}/book", headers=donor)
    later_booking = bbms.http.post(f"/api/drives/slots/{later['slots'][0]['id']}/book", headers=donor)
    assert soon_booking.status_code == 201 and later_booking.status_code == 201

    sent = bbms.http.post("/api/drives/reminders/send", headers=admin).json()
    assert sent["reminders_sent"] == 1 and sent["booking_ids"] == [soon_booking.json()["id"]]
    reminded = {b["id"]: b["reminder_sent_at"] for b in bbms.http.get("/api/drives/bookings/me", headers=donor).json()}
    assert reminded[soon_booking.json()["id"]] is not None
    assert reminded[later_booking.json()["id"]] is None

    assert bbms.http.post("/api/drives/reminders/send", headers=admin).json()["reminders_sent"] == 0


def test_st12_low_stock_alerts_and_emergency_callout(bbms):
    """ST-12 / BLOOD-25, BLOOD-26 (Sprint 2 additions): staff see low and out-of-stock groups
    and can call out compatible donors."""
    staff = bbms.staff()
    for _ in range(3):
        bbms.log_bag(staff, "O-", "RBC")
    for _ in range(2):
        bbms.log_bag(staff, "A+", "RBC")

    alerts = bbms.http.get("/api/inventory/low-stock", headers=staff, params={"threshold": 2}).json()
    by_key = {(a["blood_group"], a["component"]): a for a in alerts}
    assert len(alerts) == 31  # 8 groups x 4 components, minus O- RBC which is above the threshold
    assert ("O-", "RBC") not in by_key
    assert by_key[("A+", "RBC")]["level"] == "LOW_STOCK" and by_key[("A+", "RBC")]["available_units"] == 2
    assert by_key[("B+", "RBC")]["level"] == "OUT_OF_STOCK"

    _, o_neg_donor = bbms.new_donor({**PROFILE, "blood_group": "O-"})
    bbms.new_donor({**PROFILE, "blood_group": "AB+"})
    callout = bbms.http.post("/api/donors/emergency-callout", headers=staff, json={
        "blood_type": "O-", "units_needed": 2, "hospital_name": "City Hospital",
    })
    assert callout.status_code == 200, callout.text
    assert callout.json()["donor_ids"] == [bbms.user_id(o_neg_donor)]

    bad = bbms.http.post("/api/donors/emergency-callout", headers=staff, json={
        "blood_type": "Z+", "units_needed": 2, "hospital_name": "City Hospital",
    })
    assert bad.status_code == 400
    assert bbms.http.get("/api/inventory/low-stock", headers=o_neg_donor).status_code == 403


def test_st13_roles_cannot_use_each_others_actions(bbms):
    """ST-13 / BBS-SR-003, test plan 5.1 RBAC: a donor is blocked from staff and admin actions,
    a hospital cannot change inventory or see another hospital's requests, and nothing
    works without logging in."""
    staff = bbms.staff()
    hospital_a, hospital_b = bbms.hospital(hospital_id=1), bbms.hospital(hospital_id=2)
    _, donor = bbms.new_donor(PROFILE)
    _, other_donor = bbms.new_donor(PROFILE)
    bag = {"blood_group": "O+", "component": "RBC", "collection_date": date.today().isoformat()}
    request_id = bbms.submit_request(hospital_a, "O+", 1)
    account = {"email": "sneaky@example.com", "password": PASSWORD, "role": "admin"}
    drive = drive_body("Donor Drive", datetime.now(timezone.utc) + timedelta(days=3))

    donor_blocked = [
        ("POST", "/api/inventory/bags", bag),
        ("GET", "/api/inventory/bags", None),
        ("POST", "/api/inventory/expire", None),
        ("GET", "/api/requests/queue", None),
        ("POST", f"/api/requests/{request_id}/approve", None),
        ("POST", f"/api/requests/{request_id}/dispatch", None),
        ("POST", "/api/admin/accounts", account),
        ("POST", "/api/drives", drive),
        ("POST", "/api/drives/reminders/send", None),
        ("GET", f"/api/donors/{bbms.user_id(other_donor)}/donations", None),
        ("POST", "/api/requests", {"blood_group": "O+", "component": "RBC", "quantity": 1}),
    ]
    for method, path, body in donor_blocked:
        assert bbms.http.request(method, path, headers=donor, json=body).status_code == 403, path
        assert bbms.http.request(method, path, json=body).status_code == 401, path

    assert bbms.http.post("/api/inventory/bags", headers=hospital_a, json=bag).status_code == 403
    assert bbms.http.post(f"/api/requests/{request_id}/approve", headers=hospital_a).status_code == 403
    assert bbms.http.post("/api/admin/accounts", headers=staff, json=account).status_code == 403
    assert bbms.http.get("/api/donors/profile", headers=staff).status_code == 403

    # Hospital B cannot read hospital A's request.
    assert bbms.http.get(f"/api/requests/{request_id}", headers=hospital_b).status_code == 404
    assert bbms.http.get("/api/requests", headers=hospital_b).json() == []
    assert bbms.http.get(f"/api/requests/{request_id}", headers=hospital_a).status_code == 200


def test_st14_passwords_and_codes_are_stored_hashed(bbms):
    """ST-14 / BBS-NF-003, BBS-SR-002: database inspection finds Argon2 hashes, no plain-text
    passwords, signup codes or session tokens; the API never returns a password."""
    email = "hashed@example.com"
    assert bbms.http.post("/api/auth/signup", json={"email": email, "password": PASSWORD}).status_code == 202
    bbms.otp_for(email)  # a signup code is now pending
    login = bbms.http.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD})
    token = login.json()["access_token"]
    assert "password" not in login.text.lower()

    hashes = [row[0] for row in bbms.sql("SELECT password_hash FROM auth_users")]
    assert len(hashes) == 2 and all(h.startswith("$argon2id$") for h in hashes)
    assert len(set(hashes)) == 2  # same password, different salt, different hash
    (code_hash,) = bbms.sql("SELECT code_hash FROM auth_signup_otps")[0]
    assert code_hash.startswith("$argon2id$")

    raw = bbms.db_path.read_bytes()
    assert PASSWORD.encode() not in raw
    assert token.encode() not in raw


def test_st15_session_ends_on_logout_and_after_inactivity(start_bbms):
    """ST-15 / BBS-SR-005: a token stops working after logout, and after the idle timeout
    (set to 4 seconds for this run) the user has to log in again."""
    bbms = start_bbms(SESSION_IDLE_TIMEOUT_SECONDS="4")
    headers = bbms.admin()
    assert bbms.http.get("/api/auth/me", headers=headers).status_code == 200
    assert bbms.http.post("/api/auth/logout", headers=headers).status_code == 204
    assert bbms.http.get("/api/auth/me", headers=headers).status_code == 401

    # Activity keeps the session alive: 4.5 seconds pass in total, never 4 without a call.
    headers = bbms.admin()
    for _ in range(3):
        time.sleep(1.5)
        assert bbms.http.get("/api/auth/me", headers=headers).status_code == 200

    time.sleep(5.5)
    assert bbms.http.get("/api/auth/me", headers=headers).status_code == 401
    assert bbms.http.get("/api/auth/me", headers=bbms.admin()).status_code == 200  # re-login works


def test_st16_malicious_input_is_rejected_cleanly(bbms):
    """ST-16 / test plan 5.1 input validation: SQL injection and script payloads never cause
    a server error, never bypass login and never damage data."""
    staff, hospital = bbms.staff(), bbms.hospital()
    _, donor = bbms.new_donor()
    injection = "' OR '1'='1' --"

    for body in (
        {"email": injection, "password": injection},
        {"email": f"sysadmin@example.com{injection}", "password": PASSWORD},
        {"email": ADMIN_EMAIL, "password": injection},
    ):
        assert bbms.http.post("/api/auth/login", json=body).status_code in (401, 422)
    assert bbms.http.get("/api/inventory/bags/" + "x' OR '1'='1", headers=staff).status_code == 404
    assert bbms.http.get("/api/requests/1 OR 1=1", headers=hospital).status_code == 422

    script = "<script>alert(1)</script>'; DROP TABLE donor_profiles; --"
    created = bbms.http.post("/api/donors/profile", headers=donor, json={**PROFILE, "full_name": script})
    assert created.status_code == 201
    # Stored and returned as plain text in JSON; the table is still there.
    profile = bbms.http.get("/api/donors/profile", headers=donor)
    assert profile.headers["content-type"].startswith("application/json")
    assert profile.json()["full_name"] == script
    assert bbms.sql("SELECT COUNT(*) FROM donor_profiles") == [(1,)]

    unknown_field = {"blood_group": "O+", "component": "RBC", "quantity": 1, "status": "APPROVED"}
    assert bbms.http.post("/api/requests", headers=hospital, json=unknown_field).status_code == 422
    assert bbms.http.post("/api/requests", headers=hospital, json={
        "blood_group": "O+", "component": "RBC", "quantity": -5,
    }).status_code == 422
    assert bbms.http.get("/api/health").status_code == 200


def test_st17_inventory_search_answers_within_two_seconds(bbms, record_property):
    """ST-17 / BBS-NF-001: with 300 units in stock, the inventory list and a unit lookup
    each answer in under 2 seconds."""
    staff = bbms.staff()
    groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
    components = ["RBC", "Plasma", "Whole Blood"]
    bags = [bbms.log_bag(staff, groups[i % 8], components[i % 3]) for i in range(300)]

    list_times, lookup_times = [], []
    for i in range(20):
        started = time.perf_counter()
        response = bbms.http.get("/api/inventory/bags", headers=staff)
        list_times.append(time.perf_counter() - started)
        assert response.status_code == 200 and len(response.json()) == 300

        started = time.perf_counter()
        response = bbms.http.get(f"/api/inventory/bags/{bags[i * 7]['unit_id']}", headers=staff)
        lookup_times.append(time.perf_counter() - started)
        assert response.status_code == 200

    record_property("list_median_ms", round(statistics.median(list_times) * 1000, 1))
    record_property("list_max_ms", round(max(list_times) * 1000, 1))
    record_property("lookup_median_ms", round(statistics.median(lookup_times) * 1000, 1))
    record_property("lookup_max_ms", round(max(lookup_times) * 1000, 1))
    assert max(list_times) < 2.0
    assert max(lookup_times) < 2.0


def test_st18_one_unit_is_never_allocated_to_two_requests(bbms):
    """ST-18 / BBS-NF-005: two staff members approve two requests for the last unit at the
    same moment; exactly one succeeds, in every one of 10 rounds."""
    staff_a, staff_b = bbms.staff(), bbms.staff()
    hospital = bbms.hospital()

    for round_number in range(10):
        unit_id = bbms.log_bag(staff_a, "AB-", "Whole Blood")["unit_id"]
        requests = [bbms.submit_request(hospital, "AB-", 1, "Whole Blood") for _ in range(2)]
        barrier = threading.Barrier(2)
        codes: dict[int, int] = {}

        def approve(request_id: int, headers: dict) -> None:
            barrier.wait()
            codes[request_id] = bbms.http.post(f"/api/requests/{request_id}/approve", headers=headers).status_code

        threads = [
            threading.Thread(target=approve, args=(requests[0], staff_a)),
            threading.Thread(target=approve, args=(requests[1], staff_b)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert sorted(codes.values()) == [200, 409], f"round {round_number}: {codes}"
        winner = next(request_id for request_id, code in codes.items() if code == 200)
        loser = next(request_id for request_id, code in codes.items() if code == 409)
        assert bbms.http.get(f"/api/requests/{winner}/units", headers=staff_a).json()["unit_ids"] == [unit_id]
        assert bbms.http.get(f"/api/requests/{loser}/units", headers=staff_a).json()["unit_ids"] == []
        assert bbms.http.get(f"/api/requests/{loser}", headers=hospital).json()["status"] == "PENDING"
        # Clear the unit so the next round starts with an empty AB- shelf.
        assert bbms.http.post(f"/api/requests/{winner}/dispatch", headers=staff_a).status_code == 200
        assert bbms.http.post(f"/api/requests/{loser}/reject", headers=staff_b, json={"reason": "no stock"}).status_code == 200
