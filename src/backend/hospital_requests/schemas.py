"""Pydantic request/response schemas for /api/requests (BLOOD-15)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from .models import BloodGroup, Component, Urgency


class SubmitRequestIn(BaseModel):
    """Body of POST /api/requests. Unknown fields are rejected."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    blood_group: BloodGroup
    component: Component
    quantity: StrictInt = Field(ge=1, description="Number of units; upper limit comes from settings")
    urgency: Urgency = "routine"
    required_by: Optional[datetime] = Field(default=None, description="ISO 8601; must be in the future")
    patient_reference: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("patient_reference", "notes")
    @classmethod
    def _blank_to_none(cls, value: Optional[str]) -> Optional[str]:
        return value or None


class BloodRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hospital_id: int
    requested_by: int
    blood_group: str
    component: str
    quantity: int
    urgency: str
    required_by: Optional[datetime]
    patient_reference: Optional[str]
    notes: Optional[str]
    status: str
    created_at: datetime
