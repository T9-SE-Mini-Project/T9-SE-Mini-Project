"""Inventory endpoints for blood bank staff (BLOOD-12, BLOOD-13, BLOOD-14)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from ..blood import BloodGroup, Component
from .service import add_blood_bag, expire_blood_units, get_blood_bag, list_available_blood_bags


class BloodBagIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blood_group: BloodGroup
    component: Component
    collection_date: date


class BloodBagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unit_id: str
    blood_group: str
    component: str
    collection_date: date
    # Filled in automatically from the component's shelf life (AC-021).
    expiry_date: date
    status: str


class ExpiryRunOut(BaseModel):
    expired_count: int


def create_inventory_router(get_session, require_role):
    router = APIRouter(prefix="/api/inventory", tags=["inventory"])
    staff_only = require_role("blood_bank_staff")

    @router.post("/bags", response_model=BloodBagOut, status_code=status.HTTP_201_CREATED)
    def log_blood_bag(payload: BloodBagIn, staff=Depends(staff_only), db=Depends(get_session)):
        try:
            return add_blood_bag(db, payload.blood_group, payload.component, payload.collection_date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/bags", response_model=list[BloodBagOut])
    def available_stock(staff=Depends(staff_only), db=Depends(get_session)):
        """Available stock only: expired and allocated bags are left out (AC-022)."""
        return list_available_blood_bags(db)

    @router.get("/bags/{unit_id}", response_model=BloodBagOut)
    def blood_bag(unit_id: str, staff=Depends(staff_only), db=Depends(get_session)):
        bag = get_blood_bag(db, unit_id)
        if bag is None:
            raise HTTPException(status_code=404, detail="Blood bag not found")
        return bag

    @router.post("/expire", response_model=ExpiryRunOut)
    def run_expiry(staff=Depends(staff_only), db=Depends(get_session)):
        """Mark expired units, logging the staff member who ran it (BBS-SR-004)."""
        return ExpiryRunOut(expired_count=expire_blood_units(db, actor_id=staff.id))

    return router
