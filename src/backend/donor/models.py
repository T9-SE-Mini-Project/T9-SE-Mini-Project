"""Donation history (BLOOD-10) and donor profile (BLOOD-9) tables."""
from datetime import date, datetime
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..auth import orm as _auth_orm  # noqa: F401  (registers auth_users for the foreign keys)
from ..database import Base


class DonationRecord(Base):
    __tablename__ = "donation_history"
    __table_args__ = (
        UniqueConstraint("donation_id", name="uq_donation_history_donation_id"),
        CheckConstraint("quantity_ml > 0", name="ck_donation_history_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    donation_id: Mapped[str] = mapped_column(String(40), nullable=False)
    donor_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth_users.id"), nullable=False, index=True)
    donation_date: Mapped[date] = mapped_column(Date, nullable=False)
    blood_group: Mapped[str] = mapped_column(String(3), nullable=False)
    quantity_ml: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DonorProfile(Base):
    __tablename__ = "donor_profiles"
    __table_args__ = (
        CheckConstraint("weight_kg > 0", name="ck_donor_profile_weight_positive"),
        CheckConstraint(
            "blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')",
            name="ck_donor_profile_blood_group",
        ),
    )

    # Matches the authenticated donor account ID and donation_history.donor_id.
    donor_id: Mapped[int] = mapped_column(Integer, ForeignKey("auth_users.id"), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    blood_group: Mapped[str] = mapped_column(String(3), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
