"""Donation drive, slot and booking tables (BBS-F-040, BBS-F-041, BBS-F-042)."""
import datetime as dt
from typing import Optional

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..auth import orm as _auth_orm  # noqa: F401  (registers auth_users for the foreign keys)
from ..database import Base


class Drive(Base):
    __tablename__ = "drives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False, index=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("auth_users.id"), nullable=False)

    slots: Mapped[list["Slot"]] = relationship(
        back_populates="drive",
        cascade="all, delete-orphan",
        order_by="Slot.start_time",
    )


class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_slots_capacity_positive"),
        # Database-level guard against overbooking (AC-041), on top of the service check.
        CheckConstraint("booked_count >= 0 AND booked_count <= capacity", name="ck_slots_not_overbooked"),
        CheckConstraint("end_time > start_time", name="ck_slots_time_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    drive_id: Mapped[int] = mapped_column(Integer, ForeignKey("drives.id"), nullable=False, index=True)
    start_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    booked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    drive: Mapped[Drive] = relationship(back_populates="slots")


class SlotBooking(Base):
    """One donor's booking. A donor can hold at most one slot per drive."""

    __tablename__ = "slot_bookings"
    __table_args__ = (
        UniqueConstraint("drive_id", "donor_id", name="uq_slot_bookings_drive_donor"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slot_id: Mapped[int] = mapped_column(Integer, ForeignKey("slots.id"), nullable=False, index=True)
    # Copied from the slot so the unique constraint above can use it.
    drive_id: Mapped[int] = mapped_column(Integer, ForeignKey("drives.id"), nullable=False)
    donor_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth_users.id"), nullable=False, index=True)
    booked_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Set once the reminder (BBS-F-042) has been sent, so each donor gets exactly one.
    reminder_sent_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    slot: Mapped[Slot] = relationship()
