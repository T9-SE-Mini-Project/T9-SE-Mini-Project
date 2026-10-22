"""Donor eligibility check (BLOOD-10).

A donor may donate only if ALL of these hold (SRS):
  - age is between 18 and 65 (both inclusive)
  - weight is at least 45 kg
  - at least 56 days have passed since their last completed donation

`check_eligibility` is a pure function (no database), so the rules are easy to test.
`check_donor_eligibility` adds the database part: it looks up the donor's last completed
donation in `donation_history`.

Date of birth and weight belong to the donor profile (BLOOD-9), which is not in this module
yet, so callers pass them in. Once the profile exists, load it and call the function below.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import DonationRecord

MIN_AGE = 18
MAX_AGE = 65
MIN_WEIGHT_KG = 45
MIN_DAYS_BETWEEN_DONATIONS = 56

# Only a completed donation starts the waiting period. A deferred or cancelled one means
# no blood was taken.
_COUNTED_STATUS = "COMPLETED"


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    # Every rule that failed, in plain language (empty when eligible).
    reasons: tuple[str, ...] = ()
    # The first day the donor may donate again, set only when the waiting-period rule fails.
    next_eligible_date: Optional[date] = None


def calculate_age(date_of_birth: date, today: date) -> int:
    """Age in whole years on `today` (a birthday counts on the day itself)."""
    before_birthday = (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    return today.year - date_of_birth.year - before_birthday


def check_eligibility(
    date_of_birth: date,
    weight_kg: float,
    last_donation_date: Optional[date] = None,
    today: Optional[date] = None,
) -> EligibilityResult:
    """Apply the three eligibility rules and report every one that fails.

    Raises ValueError for invalid input (not for an ineligible donor).
    """
    today = today if today is not None else date.today()
    _require_date(today, "today")
    _require_date(date_of_birth, "date of birth")
    if date_of_birth > today:
        raise ValueError("Invalid date of birth")
    _require_weight(weight_kg)
    if last_donation_date is not None:
        _require_date(last_donation_date, "last donation date")
        if last_donation_date > today:
            raise ValueError("Invalid last donation date")

    reasons: list[str] = []
    next_eligible_date: Optional[date] = None

    age = calculate_age(date_of_birth, today)
    if not MIN_AGE <= age <= MAX_AGE:
        reasons.append(f"Donor must be between {MIN_AGE} and {MAX_AGE} years old (is {age})")

    if weight_kg < MIN_WEIGHT_KG:
        reasons.append(f"Donor must weigh at least {MIN_WEIGHT_KG} kg (is {weight_kg:g} kg)")

    if last_donation_date is not None:
        days_since = (today - last_donation_date).days
        if days_since < MIN_DAYS_BETWEEN_DONATIONS:
            next_eligible_date = last_donation_date + timedelta(days=MIN_DAYS_BETWEEN_DONATIONS)
            reasons.append(
                f"At least {MIN_DAYS_BETWEEN_DONATIONS} days must pass between donations "
                f"({days_since} days since the last one)"
            )

    return EligibilityResult(eligible=not reasons, reasons=tuple(reasons), next_eligible_date=next_eligible_date)


def get_last_donation_date(db: Session, donor_id: int) -> Optional[date]:
    """Date of the donor's most recent completed donation, or None if they have none."""
    _require_donor_id(donor_id)
    query = select(func.max(DonationRecord.donation_date)).where(
        DonationRecord.donor_id == donor_id,
        DonationRecord.status == _COUNTED_STATUS,
    )
    return db.scalar(query)


def check_donor_eligibility(
    db: Session,
    donor_id: int,
    date_of_birth: date,
    weight_kg: float,
    today: Optional[date] = None,
) -> EligibilityResult:
    """Eligibility for a donor, using their donation history for the waiting-period rule."""
    last_donation = get_last_donation_date(db, donor_id)
    return check_eligibility(date_of_birth, weight_kg, last_donation, today)


def _require_donor_id(donor_id: int) -> None:
    if not isinstance(donor_id, int) or isinstance(donor_id, bool) or donor_id <= 0:
        raise ValueError("Invalid donor ID")


def _require_date(value: date, name: str) -> None:
    # datetime is a subclass of date, so it has to be excluded explicitly.
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValueError(f"Invalid {name}")


def _require_weight(weight_kg: float) -> None:
    # bool is a subclass of int, so exclude it explicitly. NaN and infinity are not weights.
    if (
        isinstance(weight_kg, bool)
        or not isinstance(weight_kg, (int, float))
        or not math.isfinite(weight_kg)
        or weight_kg <= 0
    ):
        raise ValueError("Invalid weight")