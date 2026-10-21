from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DonationRecord

BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
DONATION_STATUSES = {"COMPLETED", "DEFERRED", "CANCELLED"}


def record_donation(db: Session, donor_id: int, donation_date: date, blood_group: str, quantity_ml: int, status: str = "COMPLETED") -> DonationRecord:
    if not isinstance(donor_id, int) or isinstance(donor_id, bool) or donor_id <= 0:
        raise ValueError("Invalid donor ID")
    if not isinstance(donation_date, date) or isinstance(donation_date, datetime) or donation_date > date.today():
        raise ValueError("Invalid donation date")
    if blood_group not in BLOOD_GROUPS:
        raise ValueError("Invalid blood group")
    if not isinstance(quantity_ml, int) or isinstance(quantity_ml, bool) or quantity_ml <= 0:
        raise ValueError("Invalid donation quantity")
    if status not in DONATION_STATUSES:
        raise ValueError("Invalid donation status")

    record = DonationRecord(
        donation_id=f"DON-{uuid4().hex.upper()}",
        donor_id=donor_id,
        donation_date=donation_date,
        blood_group=blood_group,
        quantity_ml=quantity_ml,
        status=status,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_donation_history(db: Session, donor_id: int) -> list[DonationRecord]:
    if not isinstance(donor_id, int) or isinstance(donor_id, bool) or donor_id <= 0:
        raise ValueError("Invalid donor ID")
    query = select(DonationRecord).where(DonationRecord.donor_id == donor_id).order_by(DonationRecord.donation_date.desc(), DonationRecord.id.desc())
    return list(db.scalars(query).all())


def get_donation_history_for_current_donor(db: Session, authenticated_donor_id: int) -> list[DonationRecord]:
    return get_donation_history(db, authenticated_donor_id)
