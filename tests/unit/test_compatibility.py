"""BLOOD-16 blood group compatibility rules (pure functions)."""
from __future__ import annotations

import pytest

from src.backend.hospital_requests.compatibility import compatible_donor_groups, is_compatible
from src.backend.hospital_requests.models import BLOOD_GROUPS, COMPONENTS

RBC_TABLE = {
    "O-": {"O-"},
    "O+": {"O+", "O-"},
    "A-": {"A-", "O-"},
    "A+": {"A+", "A-", "O+", "O-"},
    "B-": {"B-", "O-"},
    "B+": {"B+", "B-", "O+", "O-"},
    "AB-": {"AB-", "A-", "B-", "O-"},
    "AB+": set(BLOOD_GROUPS),
}


@pytest.mark.parametrize("recipient,expected", RBC_TABLE.items())
def test_rbc_follows_the_standard_table(recipient, expected):
    assert compatible_donor_groups(recipient, "RBC") == expected


@pytest.mark.parametrize("group", BLOOD_GROUPS)
def test_whole_blood_needs_an_identical_group(group):
    assert compatible_donor_groups(group, "Whole Blood") == {group}


@pytest.mark.parametrize(
    "recipient,expected",
    [
        ("AB+", {"AB+", "AB-"}),
        ("AB-", {"AB+", "AB-"}),
        ("A+", {"A+", "A-", "AB+", "AB-"}),
        ("B-", {"B+", "B-", "AB+", "AB-"}),
        ("O+", set(BLOOD_GROUPS)),
    ],
)
def test_plasma_follows_reverse_abo_and_ignores_rh(recipient, expected):
    assert compatible_donor_groups(recipient, "Plasma") == expected


@pytest.mark.parametrize(
    "recipient,expected",
    [("A+", {"A+", "A-"}), ("A-", {"A-"}), ("O-", {"O-"}), ("AB+", {"AB+", "AB-"})],
)
def test_platelets_match_abo_and_protect_rh_negative_patients(recipient, expected):
    assert compatible_donor_groups(recipient, "Platelets") == expected


@pytest.mark.parametrize("component", COMPONENTS)
def test_a_positive_request_never_gets_b_negative(component):
    assert not is_compatible("B-", "A+", component)


@pytest.mark.parametrize("component", COMPONENTS)
@pytest.mark.parametrize("group", BLOOD_GROUPS)
def test_every_group_is_compatible_with_itself(group, component):
    assert is_compatible(group, group, component)


@pytest.mark.parametrize("component", ["RBC", "Whole Blood", "Platelets"])
@pytest.mark.parametrize("recipient", [g for g in BLOOD_GROUPS if g.endswith("-")])
def test_rh_negative_patients_never_get_rh_positive_cells(recipient, component):
    assert all(donor.endswith("-") for donor in compatible_donor_groups(recipient, component))


def test_unknown_inputs_are_rejected():
    with pytest.raises(ValueError):
        compatible_donor_groups("C+", "RBC")
    with pytest.raises(ValueError):
        compatible_donor_groups("A+", "Water")
    assert is_compatible("???", "A+", "RBC") is False
