from datetime import date, datetime
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import BloodBag

BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
COMPONENTS = {"Whole Blood", "RBC", "Platelets", "Plasma"}


def add_blood_bag(db: Session, blood_group: str, component: str, collection_date: date) -> BloodBag:
    if blood_group not in BLOOD_GROUPS:
        raise ValueError("Invalid blood group")
    if component not in COMPONENTS:
        raise ValueError("Invalid blood component")
    if not isinstance(collection_date, date) or isinstance(collection_date, datetime):
        raise ValueError("Invalid collection date")
    if collection_date > date.today():
        raise ValueError("Collection date cannot be in the future")

    bag = BloodBag(
        unit_id=f"BBU-{uuid4().hex.upper()}",
        blood_group=blood_group,
        component=component,
        collection_date=collection_date,
    )
    db.add(bag)
    db.commit()
    db.refresh(bag)
    return bag


def get_blood_bag(db: Session, unit_id: str) -> BloodBag | None:
    return db.scalar(select(BloodBag).where(BloodBag.unit_id == unit_id))
