"""Login, identity, and logout endpoints for BLOOD-6."""

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field

from .dependencies import get_session_token
from .models import Role
from .repository import AccountRepository
from .service import AuthService, AuthenticationError
from .sessions import SessionService


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class UserOutput(BaseModel):
    id: int
    role: Role
    hospital_id: int | None = None


class LoginOutput(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOutput


def create_router(get_session, get_current_user, idle_timeout_seconds=900):
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post("/login", response_model=LoginOutput)
    def login(
        payload: LoginInput,
        response: Response,
        db=Depends(get_session),
    ):
        try:
            user = AuthService(AccountRepository(db)).authenticate(
                payload.email, payload.password
            )
        except AuthenticationError as exc:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        token = SessionService(db, idle_timeout_seconds).create(user.id)
        response.headers["Cache-Control"] = "no-store"
        return LoginOutput(
            access_token=token,
            user=UserOutput(
                id=user.id,
                role=user.role,
                hospital_id=user.hospital_id,
            ),
        )

    @router.get("/me", response_model=UserOutput)
    def me(response: Response, user=Depends(get_current_user)):
        response.headers["Cache-Control"] = "no-store"
        return UserOutput(
            id=user.id,
            role=user.role,
            hospital_id=user.hospital_id,
        )

    @router.post("/logout", status_code=204)
    def logout(
        token: str = Depends(get_session_token),
        db=Depends(get_session),
    ):
        SessionService(db, idle_timeout_seconds).revoke(token)
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    return router
