"""Donor endpoints: eligibility (BLOOD-10, BBS-F-011) and donation history (BBS-F-012).

Donors see their own data only, using the ID of the logged-in account. Staff record
donations and can look up any donor's history.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from .donations import DonationNotAllowedError, record_donation_for_donor
from .eligibility import ProfileMissingError, check_profile_eligibility
from .service import get_donation_history

DonationStatus = Literal["COMPLETED", "DEFERRED", "CANCELLED"]


class EligibilityOut(BaseModel):
    eligible: bool
    reasons: list[str]
    next_eligible_date: Optional[date]


class DonationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    donation_id: str
    donor_id: int
    donation_date: date
    blood_group: str
    quantity_ml: int
    status: str
    recorded_at: datetime


class DonationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    donation_date: date
    quantity_ml: int = Field(gt=0, le=1000)
    status: DonationStatus = "COMPLETED"


class RecordedDonationOut(BaseModel):
    donation: DonationOut
    # Bag added to inventory for a completed donation, else None.
    unit_id: Optional[str]


def create_donor_router(get_session, require_role):
    router = APIRouter(prefix="/api/donors", tags=["donors"])
    donor_only = require_role("donor")
    staff_only = require_role("blood_bank_staff")

    # ----- donor -----

    @router.get("/me/eligibility", response_model=EligibilityOut)
    def my_eligibility(donor=Depends(donor_only), db=Depends(get_session)):
        try:
            result = check_profile_eligibility(db, donor.id)
        except ProfileMissingError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return EligibilityOut(
            eligible=result.eligible,
            reasons=list(result.reasons),
            next_eligible_date=result.next_eligible_date,
        )

    @router.get("/me/donations", response_model=list[DonationOut])
    def my_donations(donor=Depends(donor_only), db=Depends(get_session)):
        return get_donation_history(db, donor.id)

    # ----- blood bank staff -----

    @router.get("/{donor_id}/donations", response_model=list[DonationOut])
    def donor_donations(donor_id: int, staff=Depends(staff_only), db=Depends(get_session)):
        try:
            return get_donation_history(db, donor_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post(
        "/{donor_id}/donations",
        response_model=RecordedDonationOut,
        status_code=status.HTTP_201_CREATED,
    )
    def record_donation(
        donor_id: int,
        payload: DonationIn,
        staff=Depends(staff_only),
        db=Depends(get_session),
    ):
        try:
            recorded = record_donation_for_donor(
                db,
                donor_id=donor_id,
                donation_date=payload.donation_date,
                quantity_ml=payload.quantity_ml,
                status=payload.status,
            )
        except ProfileMissingError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except DonationNotAllowedError as exc:
            raise HTTPException(
                status_code=409,
                detail={"error": "not_eligible", "reasons": list(exc.reasons)},
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RecordedDonationOut(
            donation=DonationOut.model_validate(recorded.donation),
            unit_id=recorded.blood_bag.unit_id if recorded.blood_bag else None,
        )

    return router
