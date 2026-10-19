"""REST routes for /api/requests.

BLOOD-15 submit, BLOOD-17 approve & dispatch, BLOOD-16 cross-match.

Authentication and RBAC belong to the auth module (BBS-SR003). `require_role` is injected
by the app and must be a dependency factory:

    require_role("hospital_rep") -> FastAPI dependency that rejects other roles and
    returns the authenticated user (an object with `id` and `hospital_id`).
    require_role("blood_bank_staff") -> same, returning a user with `id`.

`cross_match` is the inventory module's CrossMatchInterface implementation.
"""
from __future__ import annotations

from typing import Callable, Iterator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .config import Settings
from .cross_match import CrossMatchInterface
from .models import (
    ROLE_HOSPITAL_REP,
    ROLE_STAFF,
    CurrentUser,
    InsufficientStockError,
    InvalidTransitionError,
    NotFoundError,
    RequestRuleError,
    StaffUser,
    Status,
    StockChangedError,
)
from .repository import RequestRepository
from .schemas import (
    AllocatedUnitsOut,
    BloodRequestOut,
    MatchPreviewOut,
    RejectIn,
    RequestEventOut,
    SubmitRequestIn,
)
from .service import RequestService

RoleGuard = Callable[[str], Callable[..., object]]

_DOMAIN_ERRORS = (NotFoundError, InvalidTransitionError, InsufficientStockError, StockChangedError)


def _to_http(exc: Exception) -> HTTPException:
    """Map a domain error to the HTTP response the client should see."""
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if isinstance(exc, InsufficientStockError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "insufficient_stock", "requested": exc.requested, "available": exc.available},
        )
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def create_router(
    get_session: Callable[[], Iterator[Session]],
    require_role: RoleGuard,
    cross_match: CrossMatchInterface,
    settings: Settings,
) -> APIRouter:
    router = APIRouter(prefix="/api/requests", tags=["hospital-requests"])
    hospital_user = require_role(ROLE_HOSPITAL_REP)
    staff_user = require_role(ROLE_STAFF)

    def get_service(session: Session = Depends(get_session)) -> RequestService:
        return RequestService(RequestRepository(session), cross_match, settings)

    # ----- blood bank staff -----
    # Fixed paths are declared before "/{request_id}" so they are never read as an id.

    @router.get("/queue", response_model=list[BloodRequestOut])
    def staff_queue(
        status_filter: Status = Query(default="PENDING", alias="status"),
        staff: StaffUser = Depends(staff_user),
        service: RequestService = Depends(get_service),
    ):
        return service.list_queue(status_filter)

    @router.get("/{request_id}/matches", response_model=MatchPreviewOut)
    def preview_matches(
        request_id: int,
        staff: StaffUser = Depends(staff_user),
        service: RequestService = Depends(get_service),
    ):
        try:
            return service.preview_matches(request_id)
        except _DOMAIN_ERRORS as exc:
            raise _to_http(exc) from exc

    @router.post("/{request_id}/approve", response_model=BloodRequestOut)
    def approve_request(
        request_id: int,
        staff: StaffUser = Depends(staff_user),
        service: RequestService = Depends(get_service),
    ):
        try:
            return service.approve(staff, request_id)
        except _DOMAIN_ERRORS as exc:
            raise _to_http(exc) from exc

    @router.post("/{request_id}/reject", response_model=BloodRequestOut)
    def reject_request(
        request_id: int,
        body: RejectIn,
        staff: StaffUser = Depends(staff_user),
        service: RequestService = Depends(get_service),
    ):
        try:
            return service.reject(staff, request_id, body.reason)
        except _DOMAIN_ERRORS as exc:
            raise _to_http(exc) from exc

    @router.post("/{request_id}/dispatch", response_model=BloodRequestOut)
    def dispatch_request(
        request_id: int,
        staff: StaffUser = Depends(staff_user),
        service: RequestService = Depends(get_service),
    ):
        try:
            return service.dispatch(staff, request_id)
        except _DOMAIN_ERRORS as exc:
            raise _to_http(exc) from exc

    @router.get("/{request_id}/units", response_model=AllocatedUnitsOut)
    def allocated_units(
        request_id: int,
        staff: StaffUser = Depends(staff_user),
        service: RequestService = Depends(get_service),
    ):
        try:
            return AllocatedUnitsOut(request_id=request_id, unit_ids=service.get_allocated_units(request_id))
        except _DOMAIN_ERRORS as exc:
            raise _to_http(exc) from exc

    @router.get("/{request_id}/history", response_model=list[RequestEventOut])
    def request_history(
        request_id: int,
        staff: StaffUser = Depends(staff_user),
        service: RequestService = Depends(get_service),
    ):
        try:
            return service.get_history(request_id)
        except _DOMAIN_ERRORS as exc:
            raise _to_http(exc) from exc

    # ----- hospital representative -----

    @router.post("", response_model=BloodRequestOut, status_code=status.HTTP_201_CREATED)
    def submit_request(
        payload: SubmitRequestIn,
        user: CurrentUser = Depends(hospital_user),
        service: RequestService = Depends(get_service),
    ):
        try:
            return service.submit_request(user, payload)
        except RequestRuleError as exc:
            raise HTTPException(
                status_code=422,
                detail=[{"loc": ["body", exc.field], "msg": exc.message}],
            ) from exc

    @router.get("", response_model=list[BloodRequestOut])
    def list_my_requests(
        user: CurrentUser = Depends(hospital_user),
        service: RequestService = Depends(get_service),
    ):
        return service.list_requests(user)

    @router.get("/{request_id}", response_model=BloodRequestOut)
    def get_request(
        request_id: int,
        user: CurrentUser = Depends(hospital_user),
        service: RequestService = Depends(get_service),
    ):
        try:
            return service.get_request(user, request_id)
        except _DOMAIN_ERRORS as exc:
            raise _to_http(exc) from exc

    return router
