from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.backend.inventory.models import Base, BloodBag
from src.backend.inventory.service import add_blood_bag, get_blood_bag


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_new_bag_gets_unique_id(db):
    bag1 = add_blood_bag(db, "A+", "RBC", date.today())
    bag2 = add_blood_bag(db, "A+", "RBC", date.today())
    assert bag1.unit_id.startswith("BBU-")
    assert bag1.unit_id != bag2.unit_id
    assert len(bag1.unit_id) == 36


def test_saved_bag_can_be_found(db):
    bag = add_blood_bag(db, "O-", "Whole Blood", date.today())
    found = get_blood_bag(db, bag.unit_id)
    assert found is not None
    assert found.blood_group == "O-"
    assert found.component == "Whole Blood"


def test_duplicate_id_rejected_by_database(db):
    bag = add_blood_bag(db, "B+", "Plasma", date.today())
    db.add(BloodBag(unit_id=bag.unit_id, blood_group="A+", component="RBC", collection_date=date.today()))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert len(db.scalars(select(BloodBag)).all()) == 1


@pytest.mark.parametrize("group,component", [("X+", "RBC"), ("A+", "Unknown")])
def test_invalid_input_rejected(db, group, component):
    with pytest.raises(ValueError):
        add_blood_bag(db, group, component, date.today())
    assert db.scalar(select(BloodBag)) is None


def test_future_collection_date_rejected(db):
    with pytest.raises(ValueError):
        add_blood_bag(db, "A+", "RBC", date.today() + timedelta(days=1))
