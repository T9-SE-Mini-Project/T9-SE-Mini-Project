from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.backend.inventory.models import Base, BloodBag, InventoryEvent
from src.backend.inventory.service import add_blood_bag, expire_blood_units, list_available_blood_bags


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_expired_at_creation(db):
    bag = add_blood_bag(db, "O-", "Platelets", date.today() - timedelta(days=8))
    assert bag.status == "EXPIRED"
    assert list_available_blood_bags(db) == []


def test_fresh_bag_available(db):
    bag = add_blood_bag(db, "A+", "RBC", date.today())
    assert bag.status == "AVAILABLE"
    assert [x.unit_id for x in list_available_blood_bags(db)] == [bag.unit_id]


def test_expiry_boundary_excluded_without_scheduler(db):
    bag = add_blood_bag(db, "A+", "Platelets", date.today())
    today = bag.expiry_date
    assert list_available_blood_bags(db, today=today) == []
    assert bag.status == "AVAILABLE"


def test_automatic_expiry_writes_audit(db):
    bag = add_blood_bag(db, "B+", "Platelets", date.today())
    count = expire_blood_units(db, actor_id=42, today=bag.expiry_date)
    db.refresh(bag)
    event = db.scalar(select(InventoryEvent))
    assert count == 1
    assert bag.status == "EXPIRED"
    assert event.unit_id == bag.unit_id
    assert event.actor_id == 42
    assert event.action == "EXPIRED"
    assert event.created_at is not None


def test_repeated_expiry_does_not_duplicate_audit(db):
    bag = add_blood_bag(db, "B-", "Platelets", date.today())
    assert expire_blood_units(db, 7, today=bag.expiry_date) == 1
    assert expire_blood_units(db, 7, today=bag.expiry_date) == 0
    assert len(db.scalars(select(InventoryEvent)).all()) == 1


def test_available_bags_exclude_allocated(db):
    bag = add_blood_bag(db, "AB+", "RBC", date.today())
    bag.status = "ALLOCATED"
    db.commit()
    assert list_available_blood_bags(db) == []


def test_only_expired_available_bags_change(db):
    old = add_blood_bag(db, "O+", "Platelets", date.today())
    fresh = add_blood_bag(db, "O+", "RBC", date.today())
    assert expire_blood_units(db, 10, today=old.expiry_date) == 1
    db.refresh(fresh)
    assert fresh.status == "AVAILABLE"
    assert [x.unit_id for x in list_available_blood_bags(db, today=old.expiry_date)] == [fresh.unit_id]


@pytest.mark.parametrize("actor", [0, -1, None, "user", True])
def test_invalid_actor_rejected(db, actor):
    with pytest.raises(ValueError):
        expire_blood_units(db, actor)
