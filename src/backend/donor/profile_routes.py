"""Donor profile endpoints for BLOOD-9."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .service import (
    DonorProfileError,
    create_donor_profile,
    get_donor_profile,
)


class ProfileInput(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    blood_group: str
    date_of_birth: date
    weight_kg: Decimal
    phone: str = Field(min_length=1, max_length=20)


class ProfileOutput(BaseModel):
    donor_id: int
    full_name: str
    blood_group: str
    date_of_birth: date
    age: int
    weight_kg: Decimal
    phone: str


def _profile_output(profile) -> ProfileOutput:
    today = date.today()
    born = profile.date_of_birth
    age = today.year - born.year - (
        (today.month, today.day) < (born.month, born.day)
    )
    return ProfileOutput(
        donor_id=profile.donor_id,
        full_name=profile.full_name,
        blood_group=profile.blood_group,
        date_of_birth=born,
        age=age,
        weight_kg=profile.weight_kg,
        phone=profile.phone,
    )


def create_profile_router(get_session, require_role):
    router = APIRouter(prefix="/api/donors/profile", tags=["donor-profile"])
    donor_only = require_role("donor")

    @router.post("", response_model=ProfileOutput, status_code=status.HTTP_201_CREATED)
    def create_my_profile(
        payload: ProfileInput,
        donor=Depends(donor_only),
        db=Depends(get_session),
    ):
        try:
            profile = create_donor_profile(
                db,
                donor_id=donor.id,
                full_name=payload.full_name,
                blood_group=payload.blood_group,
                date_of_birth=payload.date_of_birth,
                weight_kg=payload.weight_kg,
                phone=payload.phone,
            )
        except DonorProfileError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _profile_output(profile)

    @router.get("", response_model=ProfileOutput)
    def get_my_profile(
        donor=Depends(donor_only),
        db=Depends(get_session),
    ):
        profile = get_donor_profile(db, donor.id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found.")
        return _profile_output(profile)

    return router
