"""Blood bag (BLOOD-12, BLOOD-13) and inventory audit (BLOOD-14) tables.

A bag moves through these statuses:

    AVAILABLE --allocate--> ALLOCATED --dispatch--> DISPATCHED
        ^                      |
        +-------release--------+
    AVAILABLE / ALLOCATED --expiry date passes--> EXPIRED
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..auth import orm as _auth_orm  # noqa: F401  (registers auth_users for the foreign key)
from ..database import Base

STATUS_AVAILABLE = "AVAILABLE"
STATUS_ALLOCATED = "ALLOCATED"
STATUS_DISPATCHED = "DISPATCHED"
STATUS_EXPIRED = "EXPIRED"


class BloodBag(Base):
    __tablename__ = "blood_bags"
    __table_args__ = (
        UniqueConstraint("unit_id", name="uq_blood_bags_unit_id"),
        Index("ix_blood_bags_status_expiry", "status", "expiry_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    unit_id: Mapped[str] = mapped_column(String(50), nullable=False)
    blood_group: Mapped[str] = mapped_column(String(3), nullable=False)
    component: Mapped[str] = mapped_column(String(20), nullable=False)
    collection_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default=STATUS_AVAILABLE)
    # The hospital request this bag is reserved for or was sent to (BLOOD-16). Plain
    # integer, no foreign key: hospital_requests owns that table (see its orm.py).
    allocated_request_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)


class InventoryEvent(Base):
    __tablename__ = "inventory_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    unit_id: Mapped[str] = mapped_column(String(50), ForeignKey("blood_bags.unit_id"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
