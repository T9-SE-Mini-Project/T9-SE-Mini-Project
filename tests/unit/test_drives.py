"""BBS-F-040 / 041 / 042: drive creation, slot booking and reminders."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.backend.auth.orm import Account
from src.backend.database import Base
from src.backend.donor.service import create_donor_profile
from src.backend.drives import service
from src.backend.drives.schemas import DriveCreate

NOW = datetime.now(timezone.utc).replace(microsecond=0)
DRIVE_DAY = (NOW + timedelta(days=3)).date()


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for donor_id in (1, 2, 3):
            session.add(Account(id=donor_id, email=f"d{donor_id}@example.com", password_hash="x", role="donor", is_verified=True))
            session.flush()
            create_donor_profile(session, donor_id, "Donor", "O+", date(1995, 1, 1), Decimal("60"), "999")
        yield session
    engine.dispose()


def at(hour: int, day: date = DRIVE_DAY) -> datetime:
    return datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc)


def drive_payload(**overrides):
    payload = {
        "name": "Campus Drive",
        "location": "PES Campus",
        "date": DRIVE_DAY,
        "slots": [{"start_time": at(9), "end_time": at(10), "capacity": 1}],
    }
    payload.update(overrides)
    return payload


def create(db, **overrides):
    return service.create_drive(db, DriveCreate(**drive_payload(**overrides)), created_by=1)


def test_drive_needs_at_least_one_slot():
    """AC-040"""
    with pytest.raises(ValidationError):
        DriveCreate(**drive_payload(slots=[]))


@pytest.mark.parametrize("slot", [
    {"start_time": at(10), "end_time": at(9)},
    {"start_time": at(9, DRIVE_DAY + timedelta(days=1)), "end_time": at(10, DRIVE_DAY + timedelta(days=1))},
])
def test_invalid_slot_times_rejected(slot):
    with pytest.raises(ValidationError):
        DriveCreate(**drive_payload(slots=[slot]))


def test_created_drive_is_listed_with_slots(db):
    drive = create(db)
    upcoming = service.list_upcoming_drives(db)
    assert [d.id for d in upcoming] == [drive.id]
    assert len(upcoming[0].slots) == 1


def test_full_slot_cannot_be_booked(db):
    """AC-041"""
    slot = create(db).slots[0]
    service.book_slot(db, slot.id, 1, clock=lambda: NOW)
    with pytest.raises(service.SlotFullError):
        service.book_slot(db, slot.id, 2, clock=lambda: NOW)
    db.refresh(slot)
    assert slot.booked_count == 1


def test_donor_cannot_book_twice_for_one_drive(db):
    drive = create(db, slots=[
        {"start_time": at(9), "end_time": at(10), "capacity": 5},
        {"start_time": at(11), "end_time": at(12), "capacity": 5},
    ])
    service.book_slot(db, drive.slots[0].id, 1, clock=lambda: NOW)
    with pytest.raises(service.AlreadyBookedError):
        service.book_slot(db, drive.slots[1].id, 1, clock=lambda: NOW)
    db.refresh(drive.slots[1])
    assert drive.slots[1].booked_count == 0


def test_started_slot_cannot_be_booked(db):
    slot = create(db).slots[0]
    with pytest.raises(service.SlotClosedError):
        service.book_slot(db, slot.id, 1, clock=lambda: at(9, DRIVE_DAY))


def test_ineligible_donor_cannot_book(db):
    slot = create(db).slots[0]
    with pytest.raises(service.NotEligibleError):
        service.book_slot(db, slot.id, 99, clock=lambda: NOW)  # no profile


class RecordingSender:
    def __init__(self):
        self.sent = []

    def send_slot_reminder(self, email, drive_name, location, start_time):
        self.sent.append((email, start_time))


def test_reminder_sent_once_before_the_slot(db):
    """AC-042"""
    slot = create(db).slots[0]
    service.book_slot(db, slot.id, 3, clock=lambda: NOW)
    sender = RecordingSender()
    day_before = lambda: at(9) - timedelta(hours=20)  # noqa: E731

    assert service.send_due_reminders(db, sender, clock=lambda: NOW).booking_ids == []  # too early
    assert len(service.send_due_reminders(db, sender, clock=day_before).booking_ids) == 1
    assert service.send_due_reminders(db, sender, clock=day_before).booking_ids == []  # no duplicate
    assert sender.sent == [("d3@example.com", at(9))]
