"""Domain constants, types and errors for hospital blood requests (BLOOD-15)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, Protocol, get_args

BloodGroup = Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
Component = Literal["Whole Blood", "RBC", "Platelets", "Plasma"]
Urgency = Literal["routine", "urgent", "emergency"]

BLOOD_GROUPS: tuple[str, ...] = get_args(BloodGroup)
COMPONENTS: tuple[str, ...] = get_args(Component)
URGENCY_LEVELS: tuple[str, ...] = get_args(Urgency)

STATUS_PENDING = "PENDING"
# Later stories (BLOOD-16 / BLOOD-17) move a request through these states.
STATUS_APPROVED = "APPROVED"
STATUS_DISPATCHED = "DISPATCHED"
STATUS_REJECTED = "REJECTED"

ROLE_HOSPITAL_REP = "hospital_rep"


class CurrentUser(Protocol):
    """What this module needs from the auth module's authenticated user."""

    id: int
    hospital_id: int


class RequestRuleError(Exception):
    """A business rule was broken (e.g. quantity above the limit)."""

    def __init__(self, field: str, message: str):
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message


class NotFoundError(Exception):
    """The request does not exist, or is not visible to the caller."""


@dataclass(frozen=True)
class BloodRequest:
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
