from datetime import date, datetime, timedelta
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import BloodBag

BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
COMPONENTS = {"Whole Blood", "RBC", "Platelets", "Plasma"}

SHELF_LIFE_DAYS = {
    "Whole Blood": 35,
    "RBC": 42,
    "Platelets": 5,
    "Plasma": 365,
}


def calculate_expiry_date(component: str, collection_date: date) -> date:
    if component not in COMPONENTS:
        raise ValueError("Invalid blood component")
    if not isinstance(collection_date, date) or isinstance(collection_date, datetime):
        raise ValueError("Invalid collection date")
    if collection_date > date.today():
        raise ValueError("Collection date cannot be in the future")
    return collection_date + timedelta(days=SHELF_LIFE_DAYS[component])


def add_blood_bag(db: Session, blood_group: str, component: str, collection_date: date) -> BloodBag:
    if blood_group not in BLOOD_GROUPS:
        raise ValueError("Invalid blood group")

    expiry_date = calculate_expiry_date(component, collection_date)
    bag = BloodBag(
        unit_id=f"BBU-{uuid4().hex.upper()}",
        blood_group=blood_group,
        component=component,
        collection_date=collection_date,
        expiry_date=expiry_date,
    )
    db.add(bag)
    db.commit()
    db.refresh(bag)
    return bag


def get_blood_bag(db: Session, unit_id: str) -> BloodBag | None:
    return db.scalar(select(BloodBag).where(BloodBag.unit_id == unit_id))
