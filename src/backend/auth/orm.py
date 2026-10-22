"""Database table owned by the authentication module."""

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class AuthBase(DeclarativeBase):
    """Metadata for tables owned by auth."""


class Account(AuthBase):
    __tablename__ = "auth_users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('donor', 'hospital_rep', 'blood_bank_staff', 'admin')",
            name="ck_auth_user_role",
        ),
        CheckConstraint(
            "role != 'hospital_rep' OR "
            "(hospital_id IS NOT NULL AND hospital_id > 0)",
            name="ck_auth_hospital_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    hospital_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )


class LoginSession(AuthBase):
    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    last_seen_at: Mapped[int] = mapped_column(Integer, nullable=False)


class SignupOTP(AuthBase):
    __tablename__ = "auth_signup_otps"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("auth_users.id"),
        primary_key=True,
    )
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[int] = mapped_column(Integer, nullable=False)
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

