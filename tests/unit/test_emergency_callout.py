"""BLOOD-26: Unit tests for emergency donor call-out service."""
from unittest.mock import MagicMock, patch
from src.backend.donor.service import trigger_emergency_callout


@patch("src.backend.donor.service.send_notification")
def test_trigger_emergency_callout_returns_dict(mock_notify):
    """TC-Don-04: Verify emergency callout returns valid summary structure."""
    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = []

    result = trigger_emergency_callout(
        db=mock_db,
        required_blood_type="O-",
        units_needed=3,
        hospital_name="City Hospital",
    )

    assert result["required_blood_type"] == "O-"
    assert result["units_requested"] == 3
    assert result["hospital_name"] == "City Hospital"
    assert result["eligible_donors_notified"] == 0
    assert result["donor_ids"] == []


@patch("src.backend.donor.service.send_notification")
def test_trigger_emergency_callout_dispatches_notifications(mock_notify):
    """TC-Don-04b: Verify notifications are dispatched to compatible donors."""
    mock_donor = MagicMock()
    mock_donor.phone = "9876543210"
    mock_donor.donor_id = 101

    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [mock_donor]

    result = trigger_emergency_callout(
        db=mock_db,
        required_blood_type="O-",
        units_needed=2,
        hospital_name="General Hospital",
    )

    assert result["eligible_donors_notified"] == 1
    assert result["donor_ids"] == [101]
    mock_notify.assert_called_once()