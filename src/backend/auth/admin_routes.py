"""Admin-only endpoint for creating staff, hospital and admin accounts."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from .accounts import AccountError, create_account
from .models import Role


class AccountInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Role
    hospital_id: int | None = Field(default=None, gt=0)


class AccountOutput(BaseModel):
    id: int
    email: str
    role: Role
    hospital_id: int | None = None


def create_admin_router(get_session, require_role):
    router = APIRouter(prefix="/api/admin", tags=["admin"])
    admin_only = require_role("admin")

    @router.post(
        "/accounts",
        response_model=AccountOutput,
        status_code=status.HTTP_201_CREATED,
    )
    def create_managed_account(
        payload: AccountInput,
        admin=Depends(admin_only),
        db=Depends(get_session),
    ):
        try:
            account = create_account(
                db,
                email=payload.email,
                password=payload.password,
                role=payload.role,
                hospital_id=payload.hospital_id,
            )
        except AccountError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return AccountOutput(
            id=account.id,
            email=account.email,
            role=account.role,
            hospital_id=account.hospital_id,
        )

    return router
