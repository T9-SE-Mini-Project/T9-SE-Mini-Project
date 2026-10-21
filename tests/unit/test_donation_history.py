from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.backend.donor.models import Base, DonationRecord
from src.backend.donor.service import get_donation_history, get_donation_history_for_current_donor, record_donation


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_new_donation_saved_with_unique_id(db):
    a = record_donation(db, 1, date.today(), "A+", 450)
    b = record_donation(db, 1, date.today(), "A+", 450)
    assert a.donation_id.startswith("DON-")
    assert a.donation_id != b.donation_id
    assert a.recorded_at is not None


def test_donation_history_is_donor_specific(db):
    record_donation(db, 1, date.today(), "O-", 450)
    record_donation(db, 2, date.today(), "B+", 350)
    history = get_donation_history_for_current_donor(db, 1)
    assert len(history) == 1
    assert history[0].donor_id == 1


def test_history_sorted_latest_first(db):
    old = record_donation(db, 1, date.today() - timedelta(days=100), "O+", 450)
    new = record_donation(db, 1, date.today() - timedelta(days=10), "O+", 450)
    assert [x.donation_id for x in get_donation_history(db, 1)] == [new.donation_id, old.donation_id]


def test_empty_history(db):
    assert get_donation_history(db, 99) == []


@pytest.mark.parametrize("donor_id", [0, -1, None, "1", True])
def test_invalid_donor_id(db, donor_id):
    with pytest.raises(ValueError):
        get_donation_history(db, donor_id)


@pytest.mark.parametrize("kwargs", [
    {"donor_id": 0},
    {"donation_date": date.today() + timedelta(days=1)},
    {"blood_group": "X+"},
    {"quantity_ml": 0},
    {"quantity_ml": True},
    {"status": "UNKNOWN"},
])
def test_invalid_donation_rejected(db, kwargs):
    params = dict(donor_id=1, donation_date=date.today(), blood_group="A+", quantity_ml=450)
    params.update(kwargs)
    with pytest.raises(ValueError):
        record_donation(db, **params)
    assert get_donation_history(db, 1) == []


def test_donation_id_unique_in_database(db):
    row = record_donation(db, 1, date.today(), "A+", 450)
    db.add(DonationRecord(donation_id=row.donation_id, donor_id=2, donation_date=date.today(), blood_group="A+", quantity_ml=400, status="COMPLETED", recorded_at=row.recorded_at))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_database_requires_positive_quantity(db):
    row = record_donation(db, 1, date.today(), "A+", 450)
    row.quantity_ml = 0
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_noncompleted_donation_is_visible_in_history(db):
    record_donation(db, 1, date.today(), "A+", 450, status="DEFERRED")
    assert get_donation_history(db, 1)[0].status == "DEFERRED"
