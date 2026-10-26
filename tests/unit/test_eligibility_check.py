from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.backend.donor.eligibility import (
    MIN_DAYS_BETWEEN_DONATIONS,
    calculate_age,
    check_donor_eligibility,
    check_eligibility,
    get_last_donation_date,
)
from src.backend.donor.models import Base
from src.backend.donor.service import record_donation

TODAY = date(2026, 10, 22)
ADULT_DOB = date(1995, 5, 10)  # 31 years old on TODAY


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def check(**overrides):
    params = dict(date_of_birth=ADULT_DOB, weight_kg=60, last_donation_date=None, today=TODAY)
    params.update(overrides)
    return check_eligibility(**params)


# ---------- age ----------

def test_calculate_age_counts_birthday_on_the_day():
    assert calculate_age(date(2008, 10, 22), TODAY) == 18
    assert calculate_age(date(2008, 10, 23), TODAY) == 17
    assert calculate_age(date(2008, 10, 21), TODAY) == 18


def test_eligible_donor_has_no_reasons():
    result = check()
    assert result.eligible is True
    assert result.reasons == ()
    assert result.next_eligible_date is None


@pytest.mark.parametrize("dob,eligible", [
    (date(2008, 10, 22), True),    # turns 18 today
    (date(2008, 10, 23), False),   # turns 18 tomorrow
    (date(1961, 10, 22), True),    # turns 65 today
    (date(1961, 10, 23), True),    # still 64
    (date(1960, 10, 22), False),   # turns 66 today
    (date(1960, 10, 23), True),    # turns 66 tomorrow, still 65 today
])
def test_age_limits_are_inclusive(dob, eligible):
    result = check(date_of_birth=dob)
    assert result.eligible is eligible
    if not eligible:
        assert "years old" in result.reasons[0]


# ---------- weight ----------

@pytest.mark.parametrize("weight,eligible", [(45, True), (45.0, True), (44.9, False), (44, False), (120, True)])
def test_minimum_weight_is_45_kg(weight, eligible):
    result = check(weight_kg=weight)
    assert result.eligible is eligible
    if not eligible:
        assert "weigh" in result.reasons[0]


# ---------- waiting period ----------

def test_never_donated_before_is_fine():
    assert check(last_donation_date=None).eligible is True


def test_exactly_56_days_since_last_donation_is_eligible():
    assert check(last_donation_date=TODAY - timedelta(days=56)).eligible is True


def test_55_days_since_last_donation_is_not_eligible():
    last = TODAY - timedelta(days=55)
    result = check(last_donation_date=last)
    assert result.eligible is False
    assert result.next_eligible_date == last + timedelta(days=MIN_DAYS_BETWEEN_DONATIONS)
    assert result.next_eligible_date == TODAY + timedelta(days=1)
    assert "56 days" in result.reasons[0]


def test_donated_today_must_wait_the_full_period():
    result = check(last_donation_date=TODAY)
    assert result.eligible is False
    assert result.next_eligible_date == TODAY + timedelta(days=56)


# ---------- several failures at once ----------

def test_every_failed_rule_is_reported():
    result = check(date_of_birth=date(2010, 1, 1), weight_kg=40, last_donation_date=TODAY - timedelta(days=10))
    assert result.eligible is False
    assert len(result.reasons) == 3
    assert result.next_eligible_date == TODAY + timedelta(days=46)


# ---------- invalid input ----------

@pytest.mark.parametrize("weight", [0, -5, None, "60", True, float("nan"), float("inf")])
def test_invalid_weight_raises(weight):
    with pytest.raises(ValueError):
        check(weight_kg=weight)


@pytest.mark.parametrize("dob", [None, "1990-01-01", TODAY + timedelta(days=1)])
def test_invalid_date_of_birth_raises(dob):
    with pytest.raises(ValueError):
        check(date_of_birth=dob)


@pytest.mark.parametrize("last", ["2026-01-01", TODAY + timedelta(days=1)])
def test_invalid_last_donation_date_raises(last):
    with pytest.raises(ValueError):
        check(last_donation_date=last)


def test_today_defaults_to_the_real_date():
    assert check_eligibility(date(1990, 1, 1), 70).eligible is True


# ---------- using the donation history ----------

def test_donor_with_no_history_is_eligible(db):
    assert check_donor_eligibility(db, 1, ADULT_DOB, 60).eligible is True
    assert get_last_donation_date(db, 1) is None


def test_recent_completed_donation_blocks_donor(db):
    last = date.today() - timedelta(days=10)
    record_donation(db, 1, last, "A+", 450)
    result = check_donor_eligibility(db, 1, ADULT_DOB, 60)
    assert result.eligible is False
    assert result.next_eligible_date == last + timedelta(days=56)


def test_most_recent_completed_donation_is_the_one_that_counts(db):
    record_donation(db, 1, date.today() - timedelta(days=300), "A+", 450)
    record_donation(db, 1, date.today() - timedelta(days=60), "A+", 450)
    assert get_last_donation_date(db, 1) == date.today() - timedelta(days=60)
    assert check_donor_eligibility(db, 1, ADULT_DOB, 60).eligible is True


@pytest.mark.parametrize("status", ["DEFERRED", "CANCELLED"])
def test_deferred_or_cancelled_donation_does_not_start_the_wait(db, status):
    record_donation(db, 1, date.today() - timedelta(days=5), "A+", 450, status=status)
    assert check_donor_eligibility(db, 1, ADULT_DOB, 60).eligible is True


def test_only_the_donors_own_history_counts(db):
    record_donation(db, 2, date.today() - timedelta(days=1), "B+", 450)
    assert check_donor_eligibility(db, 1, ADULT_DOB, 60).eligible is True
    assert check_donor_eligibility(db, 2, ADULT_DOB, 60).eligible is False


@pytest.mark.parametrize("donor_id", [0, -1, None, "1", True])
def test_invalid_donor_id_raises(db, donor_id):
    with pytest.raises(ValueError):
        check_donor_eligibility(db, donor_id, ADULT_DOB, 60)