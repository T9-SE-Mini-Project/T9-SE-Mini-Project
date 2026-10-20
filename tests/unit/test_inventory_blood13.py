from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.backend.inventory.models import Base
from src.backend.inventory.service import add_blood_bag, calculate_expiry_date, get_blood_bag, SHELF_LIFE_DAYS


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.mark.parametrize("component,days", [
    ("Whole Blood", 35),
    ("RBC", 42),
    ("Platelets", 5),
    ("Plasma", 365),
])
def test_calculate_component_expiry(component, days):
    collected = date.today() - timedelta(days=2)
    assert calculate_expiry_date(component, collected) == collected + timedelta(days=days)


@pytest.mark.parametrize("component", ["Whole Blood", "RBC", "Platelets", "Plasma"])
def test_saved_bag_has_expiry_date(db, component):
    collected = date.today() - timedelta(days=2)
    bag = add_blood_bag(db, "A+", component, collected)
    saved = get_blood_bag(db, bag.unit_id)
    assert saved.expiry_date == collected + timedelta(days=SHELF_LIFE_DAYS[component])


def test_unknown_component_rejected():
    with pytest.raises(ValueError):
        calculate_expiry_date("Unknown", date.today())


@pytest.mark.parametrize("collected", ["2026-01-01", datetime.now(), None])
def test_invalid_collection_date_rejected(collected):
    with pytest.raises(ValueError):
        calculate_expiry_date("RBC", collected)


def test_future_collection_date_rejected():
    with pytest.raises(ValueError):
        calculate_expiry_date("RBC", date.today() + timedelta(days=1))


def test_invalid_bag_does_not_save(db):
    with pytest.raises(ValueError):
        add_blood_bag(db, "A+", "Invalid", date.today())
    assert db.query(__import__("src.backend.inventory.models", fromlist=["BloodBag"]).BloodBag).count() == 0
