"""HTTP routes for BLOOD-7 donor signup and OTP verification."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from .signup import OTPSender, SignupError, SignupService


class SignupInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class OTPInput(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^[0-9]{6}$")


class ResendInput(BaseModel):
    email: EmailStr


def create_signup_router(get_session, sender: OTPSender):
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post("/signup", status_code=status.HTTP_202_ACCEPTED)
    def signup(payload: SignupInput, db=Depends(get_session)):
        try:
            SignupService(db, sender).register_donor(
                payload.email, payload.password
            )
        except SignupError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        return {"message": "Verification code sent."}

    @router.post("/signup/verify")
    def verify_signup(payload: OTPInput, db=Depends(get_session)):
        try:
            SignupService(db, sender).verify_signup(
                payload.email, payload.code
            )
        except SignupError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {"message": "Signup verified. You can now log in."}

    @router.post("/signup/resend", status_code=status.HTTP_202_ACCEPTED)
    def resend_signup_otp(payload: ResendInput, db=Depends(get_session)):
        try:
            SignupService(db, sender).resend_otp(payload.email)
        except SignupError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {"message": "New verification code sent."}

    return router
