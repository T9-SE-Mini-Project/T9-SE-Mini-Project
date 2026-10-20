"""Roles and authenticated-user details for BLOOD-6."""

from dataclasses import dataclass
from typing import Literal, Optional, get_args


Role = Literal["donor", "hospital_rep", "blood_bank_staff", "admin"]
ROLES: tuple[str, ...] = get_args(Role)


@dataclass(frozen=True)
class AuthenticatedUser:
    """Trusted user details returned by authentication, without a password."""

    id: int
    role: Role
    hospital_id: Optional[int] = None

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise ValueError("User ID must be positive.")
        if self.role not in ROLES:
            raise ValueError("Unknown user role.")
        if self.role == "hospital_rep":
            if self.hospital_id is None or self.hospital_id <= 0:
                raise ValueError(
                    "Hospital representatives must have a valid hospital ID."
                )
