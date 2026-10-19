"""BLOOD-16 Cross-match compatible units: allocation, rollback, preview and HTTP tests."""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from hospital_requests.models import InsufficientStockError, InvalidTransitionError, NotFoundError, StockChangedError
from hospital_requests.schemas import SubmitRequestIn
from hospital_requests.service import RequestService
from support import (
    NOW, SETTINGS, STAFF, STAFF_H, USER, FakeInventory, FakeUnit, create_via_api, submit, valid_payload,
)

# default stock for an A+ RBC request: AP-1..AP-5 and ON-1..ON-2 fit (7 units); BN-1 (B-) never does.
A_POS_AND_O_NEG = {"AP-1", "AP-2", "AP-3", "AP-4", "AP-5", "ON-1", "ON-2"}

# ---------- allocation on approve ----------


def test_approve_allocates_requested_number_of_units(service, inventory):
    req = submit(service, quantity=2)
    service.approve(STAFF, req.id)
    ids = service.get_allocated_units(req.id)
    assert len(ids) == 2
    assert {inventory.allocated[i] for i in ids} == {req.id}
    assert service.get_request(USER, req.id).status == "APPROVED"


def test_exact_group_is_used_before_universal_donor(service):
    req = submit(service, quantity=5)
    service.approve(STAFF, req.id)
    assert set(service.get_allocated_units(req.id)) == {"AP-1", "AP-2", "AP-3", "AP-4", "AP-5"}


def test_compatible_group_fills_the_gap_but_never_an_incompatible_one(service):
    req = submit(service, quantity=7)
    service.approve(STAFF, req.id)
    ids = set(service.get_allocated_units(req.id))
    assert ids == A_POS_AND_O_NEG
    assert "BN-1" not in ids


def test_two_requests_never_share_a_unit(service):
    first, second = submit(service, quantity=3), submit(service, quantity=3)
    service.approve(STAFF, first.id)
    service.approve(STAFF, second.id)
    a, b = set(service.get_allocated_units(first.id)), set(service.get_allocated_units(second.id))
    assert len(a) == len(b) == 3 and a.isdisjoint(b)


def test_insufficient_stock_changes_nothing(service, inventory):
    req = submit(service, quantity=8)
    with pytest.raises(InsufficientStockError) as exc:
        service.approve(STAFF, req.id)
    assert (exc.value.requested, exc.value.available) == (8, 7)
    assert service.list_queue("PENDING")[0].id == req.id
    assert inventory.allocated == {}
    assert service.get_allocated_units(req.id) == []
    assert [e.action for e in service.get_history(req.id)] == ["SUBMITTED"]


def test_reject_does_not_touch_inventory(service, inventory):
    req = submit(service)
    inventory.units.clear()
    assert service.reject(STAFF, req.id, "No stock").status == "REJECTED"
    assert inventory.allocate_calls == 0 and service.get_allocated_units(req.id) == []


# ---------- safety net: bad data from inventory ----------

E = FakeUnit


@pytest.mark.parametrize(
    "returned,available",
    [
        ([E("X1", "B-", "RBC"), E("X2", "B-", "RBC")], 0),  # wrong blood group
        ([E("X3", "A+", "Plasma"), E("X4", "A+", "Plasma")], 0),  # wrong component
        ([E("X5", "A+", "RBC"), E("X5", "A+", "RBC")], 1),  # same bag listed twice
    ],
)
def test_units_that_do_not_fit_are_ignored(repo, returned, available):
    class BrokenInventory(FakeInventory):
        def find_compatible_units(self, blood_group, component, quantity):
            return returned

    broken = BrokenInventory([])
    service = RequestService(repo, broken, SETTINGS, clock=lambda: NOW)
    req = submit(service, quantity=2)
    with pytest.raises(InsufficientStockError) as exc:
        service.approve(STAFF, req.id)
    assert exc.value.available == available
    assert broken.allocate_calls == 0


# ---------- concurrency and rollback ----------


def test_units_taken_by_someone_else_are_reported(service, inventory, monkeypatch):
    req = submit(service)
    monkeypatch.setattr(inventory, "allocate_units", lambda ids, request_id: False)
    with pytest.raises(StockChangedError):
        service.approve(STAFF, req.id)
    assert service.list_queue("PENDING")[0].id == req.id
    assert service.get_allocated_units(req.id) == []


def test_losing_the_approval_race_releases_the_units(service, inventory, repo):
    """Another staff member rejects the request after we reserved units but before we saved."""
    req = submit(service)

    def other_staff_acts():
        repo.transition(request_id=req.id, from_status="PENDING", to_status="REJECTED",
                        actor_id=21, note="duplicate", at=NOW)

    inventory.after_allocate = other_staff_acts
    with pytest.raises(InvalidTransitionError):
        service.approve(STAFF, req.id)
    assert inventory.allocated == {}
    assert service.get_allocated_units(req.id) == []


def test_database_failure_releases_the_units(service, inventory, repo, monkeypatch):
    req = submit(service)

    def boom(**kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(repo, "transition", boom)
    with pytest.raises(RuntimeError):
        service.approve(STAFF, req.id)
    assert inventory.allocated == {}


def test_a_unit_cannot_be_recorded_for_two_requests(repo):
    data = SubmitRequestIn(**valid_payload())
    first = repo.create(hospital_id=1, requested_by=7, data=data, required_by=None, created_at=NOW)
    second = repo.create(hospital_id=1, requested_by=7, data=data, required_by=None, created_at=NOW)
    common = dict(from_status="PENDING", to_status="APPROVED", actor_id=20, note=None, at=NOW)
    assert repo.transition(request_id=first.id, unit_ids=["U-1"], **common) is True
    with pytest.raises(IntegrityError):
        repo.transition(request_id=second.id, unit_ids=["U-1"], **common)
    assert repo.get(second.id).status == "PENDING"


# ---------- preview ----------


def test_preview_lists_units_without_reserving(service, inventory):
    req = submit(service, quantity=2)
    preview = service.preview_matches(req.id)
    assert preview.sufficient and len(preview.units) == 2
    assert inventory.allocated == {}
    assert service.list_queue("PENDING")[0].id == req.id


def test_preview_reports_a_shortage(service):
    req = submit(service, quantity=9)
    preview = service.preview_matches(req.id)
    assert not preview.sufficient and len(preview.units) == 7


def test_preview_only_for_pending_requests(service):
    req = submit(service)
    service.approve(STAFF, req.id)
    with pytest.raises(InvalidTransitionError):
        service.preview_matches(req.id)
    with pytest.raises(NotFoundError):
        service.preview_matches(999)


# ---------- HTTP layer ----------


def test_api_approve_allocates_units(client):
    rid = create_via_api(client, quantity=2)
    assert client.post(f"/api/requests/{rid}/approve", headers=STAFF_H).status_code == 200
    body = client.get(f"/api/requests/{rid}/units", headers=STAFF_H).json()
    assert body["request_id"] == rid and len(body["unit_ids"]) == 2


def test_api_insufficient_stock_is_409_with_numbers(client):
    rid = create_via_api(client, quantity=8)
    resp = client.post(f"/api/requests/{rid}/approve", headers=STAFF_H)
    assert resp.status_code == 409
    assert resp.json()["detail"] == {"error": "insufficient_stock", "requested": 8, "available": 7}
    assert client.get(f"/api/requests/{rid}/units", headers=STAFF_H).json()["unit_ids"] == []


def test_api_matches_preview(client):
    rid = create_via_api(client, quantity=2)
    body = client.get(f"/api/requests/{rid}/matches", headers=STAFF_H).json()
    assert body["sufficient"] is True and body["requested_quantity"] == 2
    assert {"unit_id", "blood_group", "component", "expiry_date"} <= set(body["units"][0])


def test_api_matches_and_units_are_staff_only(client):
    rid = create_via_api(client)
    for path in (f"/api/requests/{rid}/matches", f"/api/requests/{rid}/units"):
        assert client.get(path, headers={"X-Test-User": "7"}).status_code == 403
        assert client.get(path).status_code == 401
    assert client.get("/api/requests/999/matches", headers=STAFF_H).status_code == 404
    assert client.get("/api/requests/999/units", headers=STAFF_H).status_code == 404
