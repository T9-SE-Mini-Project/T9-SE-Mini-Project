"""Blood group compatibility rules (BLOOD-16).

Pure functions, no I/O. `compatible_donor_groups(recipient, component)` answers: which
donor blood groups may be given to a patient of this group, for this component?

The inventory module is the one that filters stock; hospital_requests uses these rules
as a safety net and double-checks every unit inventory returns. Aditya can copy this
table into inventory, or the team can move it to a shared module.

Rules used (standard transfusion practice, kept deliberately simple):
  - RBC:         standard red-cell table (O- is the universal donor, AB+ the universal recipient).
  - Whole Blood: identical ABO and Rh only.
  - Plasma:      reverse of RBC for ABO (AB plasma is universal), Rh is ignored.
  - Platelets:   identical ABO; an Rh-negative patient only gets Rh-negative, an Rh-positive
                 patient may get either.
"""
from __future__ import annotations

from .models import BLOOD_GROUPS, COMPONENTS

_RBC_DONORS: dict[str, frozenset[str]] = {
    "O-": frozenset({"O-"}),
    "O+": frozenset({"O+", "O-"}),
    "A-": frozenset({"A-", "O-"}),
    "A+": frozenset({"A+", "A-", "O+", "O-"}),
    "B-": frozenset({"B-", "O-"}),
    "B+": frozenset({"B+", "B-", "O+", "O-"}),
    "AB-": frozenset({"AB-", "A-", "B-", "O-"}),
    "AB+": frozenset(BLOOD_GROUPS),
}

# Recipient ABO -> ABO types whose plasma they can receive.
_PLASMA_DONOR_ABO: dict[str, tuple[str, ...]] = {
    "O": ("O", "A", "B", "AB"),
    "A": ("A", "AB"),
    "B": ("B", "AB"),
    "AB": ("AB",),
}


def _split(group: str) -> tuple[str, str]:
    if group not in BLOOD_GROUPS:
        raise ValueError(f"Unknown blood group: {group!r}")
    return group[:-1], group[-1]


def compatible_donor_groups(recipient: str, component: str) -> frozenset[str]:
    """Donor blood groups that may be given to `recipient` for `component`."""
    abo, rh = _split(recipient)
    if component == "Whole Blood":
        return frozenset({recipient})
    if component == "RBC":
        return _RBC_DONORS[recipient]
    if component == "Plasma":
        return frozenset(f"{d}{r}" for d in _PLASMA_DONOR_ABO[abo] for r in "+-")
    if component == "Platelets":
        rhs = "-" if rh == "-" else "+-"
        return frozenset(f"{abo}{r}" for r in rhs)
    raise ValueError(f"Unknown component: {component!r} (expected one of {', '.join(COMPONENTS)})")


def is_compatible(donor: str, recipient: str, component: str) -> bool:
    """True if a `donor` group unit of `component` may be given to a `recipient`."""
    return donor in compatible_donor_groups(recipient, component)
