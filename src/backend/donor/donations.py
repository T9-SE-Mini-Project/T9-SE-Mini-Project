"""Recording a donation end to end (BBS-F-011, BBS-F-012, BBS-F-020).

When staff record a donation, three modules are involved:
  1. donor profile    - supplies the donor's blood group, so staff cannot mistype it;
  2. eligibility      - a COMPLETED donation is only accepted from an eligible donor;
  3. inventory        - a COMPLETED donation produces one Whole Blood bag in stock.

DEFERRED and CANCELLED donations are kept in the history but take no blood, so they
skip the eligibility check and create no bag.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..inventory.models import BloodBag
from ..inventory.service import add_blood_bag
from .eligibility import ProfileMissingError, check_profile_eligibility
from .models import DonationRecord, DonorProfile
from .service import record_donation

# A donation is collected as whole blood; staff split it into components later.
COLLECTED_COMPONENT = "Whole Blood"


class DonationNotAllowedError(ValueError):
    """The donor is not eligible, so a completed donation cannot be recorded."""

    def __init__(self, reasons: tuple[str, ...]):
        super().__init__("; ".join(reasons))
        self.reasons = reasons


@dataclass(frozen=True)
class RecordedDonation:
    donation: DonationRecord
    # The bag added to inventory, or None for a DEFERRED / CANCELLED donation.
    blood_bag: Optional[BloodBag]


def record_donation_for_donor(
    db: Session,
    donor_id: int,
    donation_date: date,
    quantity_ml: int,
    status: str = "COMPLETED",
) -> RecordedDonation:
    """Save a donation in the donor's history and, if completed, add the bag to stock.

    Raises ProfileMissingError if the donor has no profile, DonationNotAllowedError if
    the donor is not eligible, and ValueError for invalid input.

    The history row and the bag are committed one after the other (both services
    commit their own work). Every input is validated before the first commit, so the
    second one can only fail on a database error.
    """
    if not isinstance(donation_date, date) or isinstance(donation_date, datetime) or donation_date > date.today():
        raise ValueError("Invalid donation date")
    profile = db.get(DonorProfile, donor_id) if isinstance(donor_id, int) else None
    if profile is None:
        raise ProfileMissingError("The donor has no profile yet")

    if status == "COMPLETED":
        try:
            result = check_profile_eligibility(db, donor_id, today=donation_date)
        except ValueError as exc:
            # e.g. a later donation is already on record
            raise DonationNotAllowedError((str(exc),)) from exc
        if not result.eligible:
            raise DonationNotAllowedError(result.reasons)

    donation = record_donation(
        db,
        donor_id=donor_id,
        donation_date=donation_date,
        blood_group=profile.blood_group,
        quantity_ml=quantity_ml,
        status=status,
    )
    bag = None
    if status == "COMPLETED":
        bag = add_blood_bag(db, profile.blood_group, COLLECTED_COMPONENT, donation_date)
    return RecordedDonation(donation=donation, blood_bag=bag)
