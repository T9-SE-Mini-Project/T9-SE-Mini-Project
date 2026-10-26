"""Contract between hospital_requests and the inventory module (CrossMatchInterface).

hospital_requests only ever talks to inventory through this interface, as in-process calls.
The inventory module (Aditya) provides an object with these three methods; it does NOT need
to import anything from hospital_requests, because typing here is structural (Protocols).

How the two modules work together when staff approve a request:

    1. find_compatible_units()  - read-only look at stock, nothing is reserved yet
    2. allocate_units()         - reserve the chosen units, all-or-nothing
    3. hospital_requests saves the APPROVED status and the unit ids in its own tables
    4. if step 3 fails or loses a race, release_units() hands the units back

And when staff dispatch an approved request (BBS-F-032):

    5. dispatch_units()         - mark the allocated units as sent, all-or-nothing
    6. hospital_requests saves the DISPATCHED status

The implementation is `inventory.cross_match.InventoryCrossMatch`.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Protocol, Sequence


class UnitLike(Protocol):
    """What hospital_requests needs to know about one blood unit (bag)."""

    @property
    def unit_id(self) -> str:
        """The unique bag ID (BLOOD-12)."""

    @property
    def blood_group(self) -> str:
        """One of A+, A-, B+, B-, AB+, AB-, O+, O-."""

    @property
    def component(self) -> str:
        """One of Whole Blood, RBC, Platelets, Plasma."""

    @property
    def expiry_date(self) -> date | datetime: ...


class CrossMatchInterface(Protocol):
    def find_compatible_units(
        self, blood_group: str, component: str, quantity: int
    ) -> Sequence[UnitLike]:
        """Return up to `quantity` units that could be given to a patient of `blood_group`.

        `blood_group` is the RECIPIENT's group. Requirements for the implementation:
          - only units that are available right now: not allocated, not expired
            (expired units are excluded at query time, no scheduler needed);
          - `component` must match exactly;
          - blood group must follow the standard compatibility rules
            (an A+ request never gets a B- unit);
          - best first: an exact group match before a compatible-but-different group
            (keeps O- for the patients who need it), then the soonest expiry;
          - read-only: this call must not reserve anything.
        Returning fewer than `quantity` units means there is not enough stock.
        """

    def allocate_units(self, unit_ids: Sequence[str], request_id: int) -> bool:
        """Reserve every unit in `unit_ids` for `request_id`, all or nothing.

        Must run in ONE database transaction and be safe against two staff allocating at
        the same time (BBS-NF005), e.g. a conditional
        `UPDATE ... SET status='ALLOCATED' WHERE id IN (...) AND status='AVAILABLE'`
        followed by a check that every row was updated, or `SELECT ... FOR UPDATE`.
        Return True if all units were reserved. If any unit is missing, expired or already
        taken, change nothing and return False (do not raise for that case).
        """

    def release_units(self, unit_ids: Sequence[str], request_id: int) -> None:
        """Undo allocate_units for these units, only if they are allocated to `request_id`.

        Used when the request could not be approved after the units were reserved.
        Must be safe to call twice (idempotent).
        """

    def dispatch_units(self, unit_ids: Sequence[str], request_id: int) -> bool:
        """Mark the units allocated to `request_id` as dispatched, all or nothing.

        Return False, changing nothing, if any unit is no longer allocated to this
        request or has expired, so expired blood is never sent out. Units already
        dispatched for this same request count as success (safe to retry).
        """
