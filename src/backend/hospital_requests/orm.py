"""SQLAlchemy mappings for the tables owned by this module.

Tables use the shared declarative `Base` from `database.py`. They deliberately have no
foreign keys into other modules' tables (see AllocationRecord).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .models import BLOOD_GROUPS, COMPONENTS, STATUS_PENDING, URGENCY_LEVELS


def _in_list(column: str, values: tuple[str, ...]) -> str:
    # Values come from module constants, never from user input.
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class BloodRequestRecord(Base):
    __tablename__ = "blood_requests"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_blood_requests_quantity_positive"),
        CheckConstraint(_in_list("blood_group", BLOOD_GROUPS), name="ck_blood_requests_group"),
        CheckConstraint(_in_list("component", COMPONENTS), name="ck_blood_requests_component"),
        CheckConstraint(_in_list("urgency", URGENCY_LEVELS), name="ck_blood_requests_urgency"),
        Index("ix_blood_requests_hospital_created", "hospital_id", "created_at"),
        Index("ix_blood_requests_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hospital_id: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_by: Mapped[int] = mapped_column(Integer, nullable=False)
    blood_group: Mapped[str] = mapped_column(String(3), nullable=False)
    component: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    urgency: Mapped[str] = mapped_column(String(10), nullable=False, default="routine")
    required_by: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    patient_reference: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default=STATUS_PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AllocationRecord(Base):
    """Which blood units were allocated to which request (BLOOD-16).

    `unit_id` is the bag ID owned by the inventory module. It is stored as plain text with
    no foreign key, because this module must not depend on another module's tables.
    The unique constraint is a safety net: one unit can never belong to two requests.
    """

    __tablename__ = "blood_request_units"
    __table_args__ = (
        UniqueConstraint("unit_id", name="uq_blood_request_units_unit"),
        Index("ix_blood_request_units_request", "request_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("blood_requests.id"), nullable=False)
    unit_id: Mapped[str] = mapped_column(String(50), nullable=False)
    allocated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RequestEventRecord(Base):
    """Audit trail for requests: every status change records the actor and timestamp
    (BBS-SR004). If the team adds a shared audit log later, swap this out."""

    __tablename__ = "blood_request_events"
    __table_args__ = (Index("ix_blood_request_events_request", "request_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("blood_requests.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(12), nullable=False)
    actor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
