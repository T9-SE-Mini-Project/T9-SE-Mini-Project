"""Business logic for hospital blood requests.

BLOOD-15 submit, BLOOD-17 approve / reject / dispatch, BLOOD-16 cross-match and allocation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Optional, Sequence

from .compatibility import is_compatible
from .config import Settings
from .cross_match import CrossMatchInterface, UnitLike
from .models import (
    ALLOWED_TRANSITIONS,
    STATUS_APPROVED,
    STATUS_DISPATCHED,
    STATUS_PENDING,
    STATUS_REJECTED,
    BloodRequest,
    CurrentUser,
    InsufficientStockError,
    InvalidTransitionError,
    MatchPreview,
    NotFoundError,
    RequestEvent,
    RequestRuleError,
    StaffUser,
    StockChangedError,
)
from .repository import RequestRepository
from .schemas import SubmitRequestIn

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC so comparisons are always timezone-aware."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class RequestService:
    """HospitalRequestInterface: submit, track, cross-match, approve, reject and dispatch.

    Shape and type checks live in the Pydantic schemas; this class enforces the rules
    that need settings, the clock, the current status or inventory. The repository, the
    inventory (CrossMatchInterface) and the clock are injected so tests can fake them.
    """

    def __init__(
        self,
        repository: RequestRepository,
        cross_match: CrossMatchInterface,
        settings: Settings,
        clock: Callable[[], datetime] = _utc_now,
    ):
        self._repo = repository
        self._cross_match = cross_match
        self._settings = settings
        self._clock = clock

    # ---------- hospital side (BLOOD-15) ----------

    def submit_request(self, user: CurrentUser, payload: SubmitRequestIn) -> BloodRequest:
        """Store a new PENDING request for the caller's hospital.

        Raises RequestRuleError if a business rule is broken.
        """
        now = self._clock()
        self._check_quantity(payload.quantity)
        required_by = self._check_required_by(payload.required_by, now)
        return self._repo.create(
            hospital_id=user.hospital_id,
            requested_by=user.id,
            data=payload,
            required_by=required_by,
            created_at=now,
        )

    def get_request(self, user: CurrentUser, request_id: int) -> BloodRequest:
        """Fetch one request, only if it belongs to the caller's hospital."""
        request = self._repo.get(request_id)
        # Same error for "missing" and "someone else's" so ids can't be probed.
        if request is None or request.hospital_id != user.hospital_id:
            raise NotFoundError(f"Request {request_id} not found")
        return request

    def list_requests(self, user: CurrentUser) -> list[BloodRequest]:
        """All requests submitted by the caller's hospital, newest first."""
        return self._repo.list_for_hospital(user.hospital_id)

    # ---------- blood bank staff side (BLOOD-17, BLOOD-16) ----------

    def list_queue(self, status: str = STATUS_PENDING) -> list[BloodRequest]:
        """Requests in a given status across all hospitals, oldest first."""
        return self._repo.list_by_status(status)

    def preview_matches(self, request_id: int) -> MatchPreview:
        """Show which units would be allocated if the request were approved now.

        Read-only: nothing is reserved, so the answer can be out of date a moment later.
        Only meaningful for PENDING requests.
        """
        request = self._load(request_id)
        self._require_transition(request, STATUS_APPROVED)
        units = self._matching_units(request)
        return MatchPreview(
            request_id=request.id,
            requested_quantity=request.quantity,
            units=units,
            sufficient=len(units) >= request.quantity,
        )

    def approve(self, staff: StaffUser, request_id: int) -> BloodRequest:
        """PENDING -> APPROVED, allocating compatible units from stock.

        Raises InsufficientStockError if stock cannot cover the request, and
        StockChangedError if another request took some of the units first.
        """
        return self._transition(staff, request_id, STATUS_APPROVED, allocate=True)

    def reject(self, staff: StaffUser, request_id: int, reason: str) -> BloodRequest:
        """PENDING -> REJECTED, keeping the reason in the history. No units are involved."""
        return self._transition(staff, request_id, STATUS_REJECTED, note=reason)

    def dispatch(self, staff: StaffUser, request_id: int) -> BloodRequest:
        """APPROVED -> DISPATCHED."""
        return self._transition(staff, request_id, STATUS_DISPATCHED)

    def get_allocated_units(self, request_id: int) -> list[str]:
        """Bag IDs allocated to the request, i.e. what to physically send."""
        self._load(request_id)
        return self._repo.list_unit_ids(request_id)

    def get_history(self, request_id: int) -> list[RequestEvent]:
        """Audit trail (who did what, when) for one request, oldest first."""
        self._load(request_id)
        return self._repo.list_events(request_id)

    # ---------- internals ----------

    def _load(self, request_id: int) -> BloodRequest:
        request = self._repo.get(request_id)
        if request is None:
            raise NotFoundError(f"Request {request_id} not found")
        return request

    @staticmethod
    def _require_transition(request: BloodRequest, target: str) -> None:
        if target not in ALLOWED_TRANSITIONS.get(request.status, ()):
            raise InvalidTransitionError(request.status, target)

    def _transition(
        self,
        staff: StaffUser,
        request_id: int,
        target: str,
        *,
        note: Optional[str] = None,
        allocate: bool = False,
    ) -> BloodRequest:
        request = self._load(request_id)
        self._require_transition(request, target)
        unit_ids = self._allocate_units(request) if allocate else []
        try:
            applied = self._repo.transition(
                request_id=request_id,
                from_status=request.status,
                to_status=target,
                actor_id=staff.id,
                note=note,
                at=self._clock(),
                unit_ids=unit_ids,
            )
        except Exception:
            self._release_units(unit_ids, request_id)
            raise
        if not applied:
            # Another staff member changed the request between our read and our write.
            self._release_units(unit_ids, request_id)
            raise InvalidTransitionError(self._load(request_id).status, target)
        return self._load(request_id)

    def _matching_units(self, request: BloodRequest) -> list[UnitLike]:
        """Ask inventory for units and keep only the ones that really fit the request.

        Inventory is expected to return compatible units already; checking again here
        means a bug on that side can never put the wrong blood group on a request.
        """
        candidates: Sequence[UnitLike] = self._cross_match.find_compatible_units(
            request.blood_group, request.component, request.quantity
        )
        chosen: list[UnitLike] = []
        seen: set[str] = set()
        for unit in candidates:
            if unit.unit_id in seen:
                continue
            if not self._fits(request, unit):
                logger.warning(
                    "Inventory returned unit %s (%s, %s) that does not fit request %s (%s, %s); ignoring it",
                    unit.unit_id, unit.blood_group, unit.component,
                    request.id, request.blood_group, request.component,
                )
                continue
            seen.add(unit.unit_id)
            chosen.append(unit)
            if len(chosen) == request.quantity:
                break
        return chosen

    @staticmethod
    def _fits(request: BloodRequest, unit: UnitLike) -> bool:
        return unit.component == request.component and is_compatible(
            unit.blood_group, request.blood_group, request.component
        )

    def _allocate_units(self, request: BloodRequest) -> list[str]:
        units = self._matching_units(request)
        if len(units) < request.quantity:
            raise InsufficientStockError(request.quantity, len(units))
        unit_ids = [unit.unit_id for unit in units]
        if not self._cross_match.allocate_units(unit_ids, request.id):
            raise StockChangedError()
        return unit_ids

    def _release_units(self, unit_ids: Sequence[str], request_id: int) -> None:
        if unit_ids:
            self._cross_match.release_units(unit_ids, request_id)

    def _check_quantity(self, quantity: int) -> None:
        limit = self._settings.max_units_per_request
        if quantity > limit:
            raise RequestRuleError("quantity", f"must be at most {limit}")

    @staticmethod
    def _check_required_by(value: datetime | None, now: datetime) -> datetime | None:
        if value is None:
            return None
        value = _as_utc(value)
        if value <= _as_utc(now):
            raise RequestRuleError("required_by", "must be in the future")
        return value
