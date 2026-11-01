"""Inventory's implementation of hospital_requests' CrossMatchInterface (BLOOD-16, BBS-F-032).

hospital_requests calls this object to find, reserve, release and dispatch blood bags.
It is created once at startup, so it opens its own short session for each call: every
method is one database transaction, as the interface requires.

Concurrency (BBS-NF-005): reserving uses a conditional UPDATE that only matches bags
still AVAILABLE. If two staff members try to take the same bag, only one UPDATE matches
it; the other sees fewer rows updated than requested, rolls back and returns False.
"""
from __future__ import annotations

from datetime import date
from typing import Callable, Sequence

from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from ..blood import compatible_donor_groups
from .models import STATUS_ALLOCATED, STATUS_AVAILABLE, STATUS_DISPATCHED, BloodBag


class InventoryCrossMatch:
    def __init__(self, session_factory: sessionmaker[Session], today: Callable[[], date] = date.today):
        self._session_factory = session_factory
        self._today = today

    def find_compatible_units(self, blood_group: str, component: str, quantity: int) -> Sequence[BloodBag]:
        """Up to `quantity` available, unexpired, compatible bags. Read-only.

        Exact blood group first (saves O- for patients who need it), then soonest expiry.
        """
        if quantity <= 0:
            return []
        donors = compatible_donor_groups(blood_group, component)
        stmt = (
            select(BloodBag)
            .where(
                BloodBag.status == STATUS_AVAILABLE,
                BloodBag.component == component,
                BloodBag.blood_group.in_(donors),
                BloodBag.expiry_date > self._today(),
            )
            .order_by(
                case((BloodBag.blood_group == blood_group, 0), else_=1),
                BloodBag.expiry_date,
                BloodBag.id,
            )
            .limit(quantity)
        )
        with self._session_factory() as session:
            return list(session.scalars(stmt))

    def allocate_units(self, unit_ids: Sequence[str], request_id: int) -> bool:
        ids = list(dict.fromkeys(unit_ids))
        if not ids:
            return False
        with self._session_factory() as session:
            result = session.execute(
                update(BloodBag)
                .where(
                    BloodBag.unit_id.in_(ids),
                    BloodBag.status == STATUS_AVAILABLE,
                    BloodBag.expiry_date > self._today(),
                )
                .values(status=STATUS_ALLOCATED, allocated_request_id=request_id)
            )
            if result.rowcount != len(ids):
                session.rollback()
                return False
            session.commit()
            return True

    def release_units(self, unit_ids: Sequence[str], request_id: int) -> None:
        if not unit_ids:
            return
        with self._session_factory() as session:
            session.execute(
                update(BloodBag)
                .where(
                    BloodBag.unit_id.in_(list(unit_ids)),
                    BloodBag.status == STATUS_ALLOCATED,
                    BloodBag.allocated_request_id == request_id,
                )
                .values(status=STATUS_AVAILABLE, allocated_request_id=None)
            )
            session.commit()

    def dispatch_units(self, unit_ids: Sequence[str], request_id: int) -> bool:
        ids = list(dict.fromkeys(unit_ids))
        if not ids:
            return False
        with self._session_factory() as session:
            already_sent = session.scalar(
                select(func.count()).select_from(BloodBag).where(
                    BloodBag.unit_id.in_(ids),
                    BloodBag.status == STATUS_DISPATCHED,
                    BloodBag.allocated_request_id == request_id,
                )
            )
            if already_sent:
                # An earlier attempt dispatched the units (all-or-nothing, so all of them).
                return already_sent == len(ids)

            result = session.execute(
                update(BloodBag)
                .where(
                    BloodBag.unit_id.in_(ids),
                    BloodBag.status == STATUS_ALLOCATED,
                    BloodBag.allocated_request_id == request_id,
                    BloodBag.expiry_date > self._today(),
                )
                .values(status=STATUS_DISPATCHED)
            )
            if result.rowcount != len(ids):
                session.rollback()
                return False
            session.commit()
            return True
