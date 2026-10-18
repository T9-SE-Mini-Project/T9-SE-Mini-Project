"""SQLAlchemy mapping for the `blood_requests` table (owned by this module).

NOTE: `Base` is a placeholder. The shared DB schema has no agreed owner yet; once the
team defines one shared declarative Base, import it here instead and generate the
Alembic migration from it. Do not edit src/database/schema.sql from this module.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .models import BLOOD_GROUPS, COMPONENTS, STATUS_PENDING, URGENCY_LEVELS


class Base(DeclarativeBase):
    pass


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
