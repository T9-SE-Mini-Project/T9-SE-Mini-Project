"""Domain constants, types and errors for hospital blood requests (BLOOD-15, BLOOD-17)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, Protocol, Sequence, get_args

from ..blood import BLOOD_GROUPS, COMPONENTS, BloodGroup, Component
from .cross_match import UnitLike

Urgency = Literal["routine", "urgent", "emergency"]
Status = Literal["PENDING", "APPROVED", "REJECTED", "DISPATCHED"]

URGENCY_LEVELS: tuple[str, ...] = get_args(Urgency)

STATUS_PENDING = "PENDING"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
STATUS_DISPATCHED = "DISPATCHED"

# Allowed status changes. Anything not listed here is rejected (409).
ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    STATUS_PENDING: (STATUS_APPROVED, STATUS_REJECTED),
    STATUS_APPROVED: (STATUS_DISPATCHED,),
}

# Extra history entry written when a request is first created.
EVENT_SUBMITTED = "SUBMITTED"

ROLE_HOSPITAL_REP = "hospital_rep"
ROLE_STAFF = "blood_bank_staff"


class CurrentUser(Protocol):
    """Hospital representative, as provided by the auth module."""

    id: int
    hospital_id: int


class StaffUser(Protocol):
    """Blood bank staff member, as provided by the auth module."""

    id: int


class RequestRuleError(Exception):
    """A business rule was broken (e.g. quantity above the limit)."""

    def __init__(self, field: str, message: str):
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message


class NotFoundError(Exception):
    """The request does not exist, or is not visible to the caller."""


class InvalidTransitionError(Exception):
    """The request is not in a state that allows the requested action."""

    def __init__(self, current: str, target: str):
        super().__init__(f"Cannot move a {current} request to {target}")
        self.current = current
        self.target = target


class InsufficientStockError(Exception):
    """Not enough compatible units in stock to cover the request (BLOOD-16)."""

    def __init__(self, requested: int, available: int):
        super().__init__(f"Requested {requested} units but only {available} compatible units are available")
        self.requested = requested
        self.available = available


class UnitsUnavailableError(Exception):
    """The units allocated to an approved request can no longer be dispatched (e.g. expired)."""

    def __init__(self) -> None:
        super().__init__(
            "Some allocated units are no longer available (they may have expired), so the request cannot be dispatched."
        )


class StockChangedError(Exception):
    """Some chosen units were allocated to someone else first. The caller can retry."""

    def __init__(self) -> None:
        super().__init__("Some of the chosen units were just allocated to another request. Please try again.")


@dataclass(frozen=True)
class MatchPreview:
    """Result of a cross-match look-up. Nothing is reserved by a preview."""

    request_id: int
    requested_quantity: int
    units: Sequence[UnitLike]
    sufficient: bool


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


@dataclass(frozen=True)
class RequestEvent:
    """One entry in a request's audit trail (who did what, and when)."""

    id: int
    request_id: int
    action: str
    actor_id: int
    note: Optional[str]
    created_at: datetime
