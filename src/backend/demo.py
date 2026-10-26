"""Demo data for trying the app locally (`python -m src.backend.cli seed-demo`).

Creates one account per role plus sample stock, donations, requests and drives, all
dated relative to today. DEVELOPMENT ONLY: the accounts share a known password.
Running it again does nothing if the demo accounts already exist.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from .auth.orm import Account
from .auth.repository import AccountRepository
from .auth.security import hash_password
from .donor.donations import record_donation_for_donor
from .donor.service import create_donor_profile
from .drives.schemas import DriveCreate
from .drives.service import create_drive
from .hospital_requests.repository import RequestRepository
from .hospital_requests.schemas import SubmitRequestIn
from .inventory.service import add_blood_bag

DEMO_PASSWORD = "Password123!"
DEMO_HOSPITAL_ID = 3

# (email, role, hospital_id)
DEMO_ACCOUNTS = [
    ("demo.admin@example.com", "admin", None),
    ("demo.staff@example.com", "blood_bank_staff", None),
    ("demo.hospital@example.com", "hospital_rep", DEMO_HOSPITAL_ID),
    ("demo.donor@example.com", "donor", None),
]

# blood group -> [(component, days since collection), ...]
DEMO_STOCK = {
    "O+": [("RBC", 3), ("RBC", 10), ("RBC", 20), ("Plasma", 40), ("Platelets", 1), ("Whole Blood", 5), ("RBC", 1), ("Plasma", 90), ("Whole Blood", 30)],
    "A+": [("RBC", 2), ("RBC", 15), ("Plasma", 10), ("Platelets", 3), ("Whole Blood", 12), ("RBC", 38), ("Plasma", 200)],
    "B+": [("RBC", 4), ("Plasma", 60), ("Platelets", 2), ("Whole Blood", 8), ("RBC", 25), ("Platelets", 1)],
    "AB+": [("Plasma", 5), ("RBC", 9), ("Platelets", 2)],
    "O-": [("RBC", 6), ("Whole Blood", 31)],
    "A-": [("RBC", 12), ("Plasma", 20), ("Platelets", 3), ("Whole Blood", 2)],
    "B-": [("RBC", 39)],
}


def seed_demo(db: Session) -> list[tuple[str, str]]:
    """Create the demo data. Returns (email, role) for every demo account."""
    accounts = [(email, role) for email, role, _ in DEMO_ACCOUNTS]
    if AccountRepository(db).get_by_email(DEMO_ACCOUNTS[0][0]) is not None:
        return accounts

    created = {}
    for email, role, hospital_id in DEMO_ACCOUNTS:
        account = Account(
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            role=role,
            hospital_id=hospital_id,
            is_active=True,
            is_verified=True,
        )
        db.add(account)
        db.flush()
        created[role] = account
    db.commit()

    today = date.today()
    donor = created["donor"]
    create_donor_profile(db, donor.id, "Aditi Sharma", "O-", date(1998, 6, 14), Decimal("58.5"), "9876543210")
    record_donation_for_donor(db, donor.id, today - timedelta(days=200), 450)
    record_donation_for_donor(db, donor.id, today - timedelta(days=120), 450, status="DEFERRED")
    record_donation_for_donor(db, donor.id, today - timedelta(days=30), 450)

    for group, bags in DEMO_STOCK.items():
        for component, age in bags:
            add_blood_bag(db, group, component, today - timedelta(days=age))

    repo = RequestRepository(db)
    hospital, staff = created["hospital_rep"], created["blood_bank_staff"]
    now = datetime.now(timezone.utc)
    for i, (group, component, quantity, urgency) in enumerate([
        ("O+", "RBC", 2, "emergency"),
        ("A+", "Plasma", 1, "routine"),
        ("B-", "RBC", 3, "urgent"),
        ("AB+", "Platelets", 2, "routine"),
    ]):
        repo.create(
            hospital_id=DEMO_HOSPITAL_ID,
            requested_by=hospital.id,
            data=SubmitRequestIn(blood_group=group, component=component, quantity=quantity,
                                 urgency=urgency, patient_reference=f"PT-10{i}"),
            required_by=now + timedelta(days=i + 1),
            created_at=now - timedelta(hours=5 * i),
        )
    approved = repo.create(
        hospital_id=DEMO_HOSPITAL_ID,
        requested_by=hospital.id,
        data=SubmitRequestIn(blood_group="A+", component="RBC", quantity=2),
        required_by=None,
        created_at=now - timedelta(days=3),
    )
    repo.transition(request_id=approved.id, from_status="PENDING", to_status="APPROVED",
                    actor_id=staff.id, note=None, at=now)

    for days_ahead, name, location, booked in [
        (4, "PES Campus Drive", "PES University, Bengaluru", (7, 5, 2)),
        (11, "City Hospital Camp", "Jayanagar 4th Block", (9, 8, 7)),
        (20, "Tech Park Drive", "Electronic City Phase 1", (6, 4, 3)),
    ]:
        day = today + timedelta(days=days_ahead)
        slots = [
            {"start_time": datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc),
             "end_time": datetime(day.year, day.month, day.day, hour + 1, tzinfo=timezone.utc),
             "capacity": 10}
            for hour in (9, 11, 14)
        ]
        drive = create_drive(db, DriveCreate(name=name, location=location, date=day, slots=slots), created_by=staff.id)
        for slot, count in zip(drive.slots, booked):
            slot.booked_count = count
        db.commit()

    return accounts
