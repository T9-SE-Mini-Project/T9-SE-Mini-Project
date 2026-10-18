"""REST routes for /api/requests (BLOOD-15).

Authentication and RBAC belong to the auth module (BBS-SR003). `require_role` is injected
by the app and must be a dependency factory:

    require_role("hospital_rep") -> FastAPI dependency that rejects other roles and
    returns the authenticated user (an object with `id` and `hospital_id`).
"""
from __future__ import annotations

from typing import Callable, Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .config import Settings
from .models import CurrentUser, NotFoundError, RequestRuleError, ROLE_HOSPITAL_REP
from .repository import RequestRepository
from .schemas import BloodRequestOut, SubmitRequestIn
from .service import RequestService

RoleGuard = Callable[[str], Callable[..., CurrentUser]]


def create_router(
    get_session: Callable[[], Iterator[Session]],
    require_role: RoleGuard,
    settings: Settings,
) -> APIRouter:
    router = APIRouter(prefix="/api/requests", tags=["hospital-requests"])
    hospital_user = require_role(ROLE_HOSPITAL_REP)

    def get_service(session: Session = Depends(get_session)) -> RequestService:
        return RequestService(RequestRepository(session), settings)

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
        except NotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found") from exc

    return router
