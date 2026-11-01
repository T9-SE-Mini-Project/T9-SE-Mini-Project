"""Business logic for donation drives (BBS-F-040, BBS-F-041, BBS-F-042)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Optional, Protocol

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..auth.orm import Account
from ..donor.eligibility import ProfileMissingError, check_profile_eligibility
from .models import Drive, Slot, SlotBooking
from .schemas import DriveCreate


class ReminderSender(Protocol):
    """Implemented by the notification service (see `notifications.py`)."""

    def send_slot_reminder(self, email: str, drive_name: str, location: str, start_time: datetime) -> None:
        """Remind a donor about their booked slot."""


class BookingError(Exception):
    """A slot could not be booked. `status_code` is the HTTP status to report."""

    status_code = 409


class SlotNotFoundError(BookingError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("Slot not found.")


class SlotFullError(BookingError):
    def __init__(self) -> None:
        super().__init__("This slot is fully booked.")


class SlotClosedError(BookingError):
    def __init__(self) -> None:
        super().__init__("This slot has already started.")


class AlreadyBookedError(BookingError):
    def __init__(self) -> None:
        super().__init__("You already have a slot booked for this drive.")


class NotEligibleError(BookingError):
    def __init__(self, reasons: tuple[str, ...]):
        super().__init__("You are not eligible to donate on the drive date: " + "; ".join(reasons))
        self.reasons = reasons


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC (SQLite drops tzinfo; PostgreSQL keeps it)."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def create_drive(db: Session, data: DriveCreate, created_by: int) -> Drive:
    """Create a drive with its slots in one transaction (BBS-F-040)."""
    drive = Drive(name=data.name, location=data.location, date=data.date, created_by=created_by)
    drive.slots = [
        Slot(
            start_time=_as_utc(slot.start_time),
            end_time=_as_utc(slot.end_time),
            capacity=slot.capacity,
            booked_count=0,
        )
        for slot in data.slots
    ]
    try:
        db.add(drive)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(drive)
    return drive


def list_upcoming_drives(db: Session, today: Optional[date] = None) -> list[Drive]:
    """Drives from today onwards, soonest first, with their slots (BBS-F-041)."""
    current = today if today is not None else date.today()
    stmt = (
        select(Drive)
        .where(Drive.date >= current)
        .options(selectinload(Drive.slots))
        .order_by(Drive.date, Drive.id)
    )
    return list(db.scalars(stmt))


def book_slot(
    db: Session,
    slot_id: int,
    donor_id: int,
    clock: Callable[[], datetime] = _utc_now,
) -> SlotBooking:
    """Book one place in a slot for a donor (BBS-F-041).

    The donor must be eligible to donate on the drive date. Capacity is enforced with a
    conditional UPDATE, so two donors racing for the last place cannot both get it
    (AC-041); the losing request sees no row updated and gets SlotFullError.
    """
    now = clock()
    slot = db.get(Slot, slot_id)
    if slot is None:
        raise SlotNotFoundError()
    if _as_utc(slot.start_time) <= _as_utc(now):
        raise SlotClosedError()

    try:
        eligibility = check_profile_eligibility(db, donor_id, today=slot.drive.date)
    except ProfileMissingError as exc:
        raise NotEligibleError((str(exc),)) from exc
    if not eligibility.eligible:
        raise NotEligibleError(eligibility.reasons)

    try:
        result = db.execute(
            update(Slot)
            .where(Slot.id == slot_id, Slot.booked_count < Slot.capacity)
            .values(booked_count=Slot.booked_count + 1)
        )
        if result.rowcount != 1:
            db.rollback()
            raise SlotFullError()
        booking = SlotBooking(slot_id=slot.id, drive_id=slot.drive_id, donor_id=donor_id, booked_at=now)
        db.add(booking)
        db.commit()
    except IntegrityError as exc:
        # The unique (drive, donor) constraint fired; the rollback also undoes the count.
        db.rollback()
        raise AlreadyBookedError() from exc
    db.refresh(booking)
    return booking


def list_bookings_for_donor(db: Session, donor_id: int) -> list[SlotBooking]:
    stmt = (
        select(SlotBooking)
        .where(SlotBooking.donor_id == donor_id)
        .options(selectinload(SlotBooking.slot))
        .order_by(SlotBooking.booked_at.desc(), SlotBooking.id.desc())
    )
    return list(db.scalars(stmt))


@dataclass(frozen=True)
class ReminderRun:
    booking_ids: list[int]


def send_due_reminders(
    db: Session,
    sender: ReminderSender,
    window: timedelta = timedelta(hours=24),
    clock: Callable[[], datetime] = _utc_now,
) -> ReminderRun:
    """Remind donors whose slot starts within `window` from now (BBS-F-042, AC-042).

    Each booking is reminded once: `reminder_sent_at` is saved right after its message
    is sent, so running this again (e.g. from a scheduler) does not send duplicates.
    """
    now = _as_utc(clock())
    stmt = (
        select(SlotBooking, Slot, Drive, Account.email)
        .join(Slot, SlotBooking.slot_id == Slot.id)
        .join(Drive, Slot.drive_id == Drive.id)
        .join(Account, SlotBooking.donor_id == Account.id)
        .where(
            SlotBooking.reminder_sent_at.is_(None),
            Slot.start_time > now,
            Slot.start_time <= now + window,
        )
        .order_by(Slot.start_time, SlotBooking.id)
    )
    sent: list[int] = []
    for booking, slot, drive, email in db.execute(stmt).all():
        sender.send_slot_reminder(email, drive.name, drive.location, _as_utc(slot.start_time))
        booking.reminder_sent_at = now
        db.commit()
        sent.append(booking.id)
    return ReminderRun(booking_ids=sent)
