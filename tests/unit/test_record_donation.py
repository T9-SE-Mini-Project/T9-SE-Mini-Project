"""BBS-F-011 / BBS-F-012: eligibility from the saved profile and recording a donation."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.backend.database import Base
from src.backend.donor.donations import DonationNotAllowedError, record_donation_for_donor
from src.backend.donor.eligibility import ProfileMissingError, check_eligibility, check_profile_eligibility
from src.backend.donor.service import create_donor_profile, get_donation_history
from src.backend.inventory.models import BloodBag

TODAY = date.today()


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def make_profile(db, donor_id=1, weight="60.5", born=date(1995, 3, 1), group="B+"):
    return create_donor_profile(db, donor_id, "Test Donor", group, born, Decimal(weight), "9876543210")


def test_decimal_weight_is_accepted():
    """The profile stores weight as NUMERIC, which loads as Decimal."""
    assert check_eligibility(date(1995, 1, 1), Decimal("45.00"), today=TODAY).eligible
    assert not check_eligibility(date(1995, 1, 1), Decimal("44.99"), today=TODAY).eligible


def test_eligibility_uses_the_saved_profile(db):
    make_profile(db, weight="40")
    result = check_profile_eligibility(db, 1)
    assert not result.eligible
    assert any("45 kg" in reason for reason in result.reasons)


def test_eligibility_needs_a_profile(db):
    with pytest.raises(ProfileMissingError):
        check_profile_eligibility(db, 99)


def test_completed_donation_is_saved_and_added_to_stock(db):
    make_profile(db)
    recorded = record_donation_for_donor(db, 1, TODAY, 450)
    assert recorded.donation.blood_group == "B+"  # taken from the profile
    assert [d.donation_id for d in get_donation_history(db, 1)] == [recorded.donation.donation_id]
    bag = db.scalar(select(BloodBag))
    assert (bag.unit_id, bag.blood_group, bag.component, bag.status) == (
        recorded.blood_bag.unit_id, "B+", "Whole Blood", "AVAILABLE"
    )


def test_ineligible_donor_cannot_donate_again_within_56_days(db):
    """AC-011: a donor who donated 30 days ago is not yet eligible."""
    make_profile(db)
    record_donation_for_donor(db, 1, TODAY - timedelta(days=30), 450)
    with pytest.raises(DonationNotAllowedError):
        record_donation_for_donor(db, 1, TODAY, 450)
    assert len(get_donation_history(db, 1)) == 1


def test_deferred_donation_skips_eligibility_and_stock(db):
    make_profile(db, weight="40")
    recorded = record_donation_for_donor(db, 1, TODAY, 450, status="DEFERRED")
    assert recorded.blood_bag is None
    assert db.scalar(select(BloodBag)) is None


@pytest.mark.parametrize("bad_date", [TODAY + timedelta(days=1), "2026-01-01", None])
def test_invalid_donation_date_rejected(db, bad_date):
    make_profile(db)
    with pytest.raises(ValueError):
        record_donation_for_donor(db, 1, bad_date, 450)
