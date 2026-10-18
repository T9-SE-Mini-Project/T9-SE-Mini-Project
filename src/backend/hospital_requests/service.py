"""Business logic for hospital blood requests (BLOOD-15 submit, BLOOD-17 approve & dispatch)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional

from .config import Settings
from .models import (
    ALLOWED_TRANSITIONS,
    STATUS_APPROVED,
    STATUS_DISPATCHED,
    STATUS_PENDING,
    STATUS_REJECTED,
    BloodRequest,
    CurrentUser,
    InvalidTransitionError,
    NotFoundError,
    RequestEvent,
    RequestRuleError,
    StaffUser,
)
from .repository import RequestRepository
from .schemas import SubmitRequestIn


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC so comparisons are always timezone-aware."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class RequestService:
    """HospitalRequestInterface: submit, track, approve, reject and dispatch requests.

    Shape and type checks live in the Pydantic schemas; this class enforces the rules
    that need settings, the clock or the current status. Repository and clock are
    injected for tests.
    """

    def __init__(
        self,
        repository: RequestRepository,
        settings: Settings,
        clock: Callable[[], datetime] = _utc_now,
    ):
        self._repo = repository
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

    # ---------- blood bank staff side (BLOOD-17) ----------

    def list_queue(self, status: str = STATUS_PENDING) -> list[BloodRequest]:
        """Requests in a given status across all hospitals, oldest first."""
        return self._repo.list_by_status(status)

    def approve(self, staff: StaffUser, request_id: int) -> BloodRequest:
        """PENDING -> APPROVED."""
        return self._transition(staff, request_id, STATUS_APPROVED, note=None)

    def reject(self, staff: StaffUser, request_id: int, reason: str) -> BloodRequest:
        """PENDING -> REJECTED, keeping the reason in the history."""
        return self._transition(staff, request_id, STATUS_REJECTED, note=reason)

    def dispatch(self, staff: StaffUser, request_id: int) -> BloodRequest:
        """APPROVED -> DISPATCHED."""
        return self._transition(staff, request_id, STATUS_DISPATCHED, note=None)

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

    def _transition(
        self, staff: StaffUser, request_id: int, target: str, note: Optional[str]
    ) -> BloodRequest:
        request = self._load(request_id)
        if target not in ALLOWED_TRANSITIONS.get(request.status, ()):
            raise InvalidTransitionError(request.status, target)
        applied = self._repo.transition(
            request_id=request_id,
            from_status=request.status,
            to_status=target,
            actor_id=staff.id,
            note=note,
            at=self._clock(),
        )
        if not applied:
            # Another staff member changed it between our read and our write.
            raise InvalidTransitionError(self._load(request_id).status, target)
        return self._load(request_id)

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
