"""Shared test helpers: constants, fake users and an in-memory fake of the inventory module."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "backend"))

from hospital_requests.compatibility import is_compatible  # noqa: E402
from hospital_requests.config import Settings  # noqa: E402
from hospital_requests.schemas import SubmitRequestIn  # noqa: E402

SETTINGS = Settings(max_units_per_request=10)

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
EXPIRY = date(2026, 11, 30)


@dataclass(frozen=True)
class FakeUser:
    id: int
    hospital_id: int
    role: str = "hospital_rep"


USER = FakeUser(id=7, hospital_id=1)
OTHER_HOSPITAL_USER = FakeUser(id=8, hospital_id=2)
STAFF = FakeUser(id=20, hospital_id=0, role="blood_bank_staff")
OTHER_STAFF = FakeUser(id=21, hospital_id=0, role="blood_bank_staff")

HOSPITAL_H = {"X-Test-User": "7"}
STAFF_H = {"X-Test-User": "20"}


def valid_payload(**overrides) -> dict:
    payload = {"blood_group": "A+", "component": "RBC", "quantity": 2, "urgency": "urgent"}
    payload.update(overrides)
    return payload


def submit(service, **overrides):
    return service.submit_request(USER, SubmitRequestIn(**valid_payload(**overrides)))


def create_via_api(client, **overrides) -> int:
    resp = client.post("/api/requests", json=valid_payload(**overrides), headers=HOSPITAL_H)
    return resp.json()["id"]


def naive(dt: datetime) -> datetime:
    """SQLite drops tzinfo; PostgreSQL keeps it. Compare on the wall-clock value."""
    return dt.replace(tzinfo=None)


@dataclass(frozen=True)
class FakeUnit:
    unit_id: str
    blood_group: str
    component: str
    expiry_date: date = EXPIRY


def default_units() -> list[FakeUnit]:
    """Stock used by most tests: 5 A+ RBC, 2 O- RBC, 1 B- RBC. An A+ request can use 7 of them."""
    return (
        [FakeUnit(f"AP-{i}", "A+", "RBC") for i in range(1, 6)]
        + [FakeUnit(f"ON-{i}", "O-", "RBC") for i in range(1, 3)]
        + [FakeUnit("BN-1", "B-", "RBC")]
    )


class FakeInventory:
    """In-memory stand-in for the inventory module (implements CrossMatchInterface)."""

    def __init__(self, units: Sequence[FakeUnit]):
        self.units = {u.unit_id: u for u in units}
        self.allocated: dict[str, int] = {}
        self.allocate_calls = 0
        self.after_allocate: Optional[Callable[[], None]] = None

    def find_compatible_units(self, blood_group: str, component: str, quantity: int):
        free = [
            u
            for u in self.units.values()
            if u.unit_id not in self.allocated
            and u.component == component
            and is_compatible(u.blood_group, blood_group, component)
        ]
        free.sort(key=lambda u: (u.blood_group != blood_group, u.expiry_date))
        return free[:quantity]

    def allocate_units(self, unit_ids: Sequence[str], request_id: int) -> bool:
        self.allocate_calls += 1
        if any(uid not in self.units or uid in self.allocated for uid in unit_ids):
            return False
        for uid in unit_ids:
            self.allocated[uid] = request_id
        if self.after_allocate:
            self.after_allocate()
        return True

    def release_units(self, unit_ids: Sequence[str], request_id: int) -> None:
        for uid in unit_ids:
            if self.allocated.get(uid) == request_id:
                del self.allocated[uid]
