"""Business logic for hospital blood requests (BLOOD-15: submit a request)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .config import Settings
from .models import BloodRequest, CurrentUser, NotFoundError, RequestRuleError
from .repository import RequestRepository
from .schemas import SubmitRequestIn


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC so comparisons are always timezone-aware."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class RequestService:
    """Submit / track part of HospitalRequestInterface.

    Shape and type checks live in the Pydantic schema; this class enforces the rules
    that need settings or the current time. Repository and clock are injected for tests.
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
