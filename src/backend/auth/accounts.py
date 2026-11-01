"""Account management for non-donor roles (BBMS admin role management).

Donors register themselves through signup (BLOOD-7). Hospital representatives, blood
bank staff and admins cannot, so an admin creates them here. The very first admin is
created from the command line (`python -m src.backend.cli create-admin`).
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import ROLES
from .orm import Account
from .repository import AccountRepository, normalize_email
from .security import hash_password


# Roles an admin may create. Donors use the public signup flow instead.
MANAGED_ROLES = tuple(role for role in ROLES if role != "donor")


class AccountError(Exception):
    """The account could not be created."""


def create_account(
    db: Session,
    email: str,
    password: str,
    role: str,
    hospital_id: int | None = None,
) -> Account:
    """Create an active, already-verified account for a managed role."""
    if role not in MANAGED_ROLES:
        raise AccountError("Role must be one of: " + ", ".join(MANAGED_ROLES) + ".")
    if role == "hospital_rep":
        if hospital_id is None or hospital_id <= 0:
            raise AccountError("Hospital representatives need a valid hospital ID.")
    elif hospital_id is not None:
        raise AccountError("Only hospital representatives have a hospital ID.")
    if not isinstance(password, str) or len(password) < 8:
        raise AccountError("Password must be at least 8 characters.")

    address = normalize_email(email)
    if AccountRepository(db).get_by_email(address) is not None:
        raise AccountError("An account with this email already exists.")

    account = Account(
        email=address,
        password_hash=hash_password(password),
        role=role,
        hospital_id=hospital_id,
        is_active=True,
        is_verified=True,
    )
    try:
        db.add(account)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AccountError("An account with this email already exists.") from exc
    db.refresh(account)
    return account
