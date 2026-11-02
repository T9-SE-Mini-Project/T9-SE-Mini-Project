from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from ..blood import BloodGroup, Component
from .low_stock import get_low_stock_alerts
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
    expiry_date: date
    status: str


class ExpiryRunOut(BaseModel):
    expired_count: int


class LowStockAlertOut(BaseModel):
    blood_group: str
    component: str
    available_units: int
    threshold: int
    level: str


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
        return list_available_blood_bags(db)

    @router.get("/low-stock", response_model=list[LowStockAlertOut])
    def low_stock(threshold: int = Query(default=5, ge=0, le=100000), staff=Depends(staff_only), db=Depends(get_session)):
        return get_low_stock_alerts(db, threshold=threshold)

    @router.get("/bags/{unit_id}", response_model=BloodBagOut)
    def blood_bag(unit_id: str, staff=Depends(staff_only), db=Depends(get_session)):
        bag = get_blood_bag(db, unit_id)
        if bag is None:
            raise HTTPException(status_code=404, detail="Blood bag not found")
        return bag

    @router.post("/expire", response_model=ExpiryRunOut)
    def run_expiry(staff=Depends(staff_only), db=Depends(get_session)):
        return ExpiryRunOut(expired_count=expire_blood_units(db, actor_id=staff.id))

    return router
