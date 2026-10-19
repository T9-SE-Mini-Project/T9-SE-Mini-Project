"""BLOOD-17 Approve & Dispatch: status rules, queue, history and HTTP tests."""
from __future__ import annotations

import pytest

from hospital_requests.models import InvalidTransitionError, NotFoundError
from hospital_requests.schemas import SubmitRequestIn
from support import HOSPITAL_H, NOW, OTHER_STAFF, STAFF, STAFF_H, create_via_api, naive, submit, valid_payload

# ---------- service ----------


def test_approve_moves_pending_to_approved_and_logs_actor(service):
    req = submit(service)
    assert service.approve(STAFF, req.id).status == "APPROVED"
    history = service.get_history(req.id)
    assert [(e.action, e.actor_id) for e in history] == [("SUBMITTED", 7), ("APPROVED", 20)]
    assert naive(history[-1].created_at) == naive(NOW)


def test_reject_requires_pending_and_keeps_reason(service):
    req = submit(service)
    assert service.reject(STAFF, req.id, "No stock").status == "REJECTED"
    assert service.get_history(req.id)[-1].note == "No stock"


def test_full_flow_pending_approved_dispatched(service):
    req = submit(service)
    service.approve(STAFF, req.id)
    assert service.dispatch(OTHER_STAFF, req.id).status == "DISPATCHED"
    assert [e.action for e in service.get_history(req.id)] == ["SUBMITTED", "APPROVED", "DISPATCHED"]


def test_cannot_dispatch_before_approval(service):
    req = submit(service)
    with pytest.raises(InvalidTransitionError):
        service.dispatch(STAFF, req.id)
    assert service.list_queue("PENDING")[0].status == "PENDING"


@pytest.mark.parametrize("first,second", [("approve", "approve"), ("reject", "approve"), ("approve", "reject")])
def test_cannot_decide_a_request_twice(service, first, second):
    req = submit(service)
    act = {
        "approve": lambda: service.approve(STAFF, req.id),
        "reject": lambda: service.reject(STAFF, req.id, "no"),
    }
    act[first]()
    with pytest.raises(InvalidTransitionError):
        act[second]()


def test_dispatched_request_is_final(service):
    req = submit(service)
    service.approve(STAFF, req.id)
    service.dispatch(STAFF, req.id)
    for action in (lambda: service.approve(STAFF, req.id), lambda: service.dispatch(STAFF, req.id)):
        with pytest.raises(InvalidTransitionError):
            action()


def test_staff_actions_on_missing_request_raise(service):
    with pytest.raises(NotFoundError):
        service.approve(STAFF, 999)
    with pytest.raises(NotFoundError):
        service.get_history(999)


def test_queue_lists_only_requested_status_oldest_first(service):
    first, second, third = submit(service), submit(service), submit(service)
    service.approve(STAFF, second.id)
    assert [r.id for r in service.list_queue("PENDING")] == [first.id, third.id]
    assert [r.id for r in service.list_queue("APPROVED")] == [second.id]


def test_transition_only_applies_from_expected_status(repo):
    """Simulates two staff racing: the second, stale update must lose and leave no history."""
    created = repo.create(
        hospital_id=1, requested_by=7, data=SubmitRequestIn(**valid_payload()), required_by=None, created_at=NOW
    )
    args = dict(request_id=created.id, from_status="PENDING", at=NOW)
    assert repo.transition(to_status="APPROVED", actor_id=20, note=None, **args) is True
    assert repo.transition(to_status="REJECTED", actor_id=21, note="late", **args) is False
    assert repo.get(created.id).status == "APPROVED"
    assert [e.action for e in repo.list_events(created.id)] == ["SUBMITTED", "APPROVED"]


# ---------- HTTP layer ----------


def test_api_staff_full_flow(client):
    rid = create_via_api(client)
    assert client.get("/api/requests/queue", headers=STAFF_H).json()[0]["id"] == rid
    assert client.post(f"/api/requests/{rid}/approve", headers=STAFF_H).json()["status"] == "APPROVED"
    assert client.post(f"/api/requests/{rid}/dispatch", headers=STAFF_H).json()["status"] == "DISPATCHED"
    history = client.get(f"/api/requests/{rid}/history", headers=STAFF_H).json()
    assert [e["action"] for e in history] == ["SUBMITTED", "APPROVED", "DISPATCHED"]
    # The hospital sees the final status on its own request.
    assert client.get(f"/api/requests/{rid}", headers=HOSPITAL_H).json()["status"] == "DISPATCHED"


def test_api_reject_needs_reason(client):
    rid = create_via_api(client)
    assert client.post(f"/api/requests/{rid}/reject", json={}, headers=STAFF_H).status_code == 422
    assert client.post(f"/api/requests/{rid}/reject", json={"reason": "  "}, headers=STAFF_H).status_code == 422
    resp = client.post(f"/api/requests/{rid}/reject", json={"reason": "Out of stock"}, headers=STAFF_H)
    assert resp.status_code == 200 and resp.json()["status"] == "REJECTED"


def test_api_invalid_transition_is_409(client):
    rid = create_via_api(client)
    assert client.post(f"/api/requests/{rid}/dispatch", headers=STAFF_H).status_code == 409
    client.post(f"/api/requests/{rid}/approve", headers=STAFF_H)
    assert client.post(f"/api/requests/{rid}/approve", headers=STAFF_H).status_code == 409


def test_api_missing_request_is_404(client):
    assert client.post("/api/requests/999/approve", headers=STAFF_H).status_code == 404
    assert client.get("/api/requests/999/history", headers=STAFF_H).status_code == 404


def test_api_staff_endpoints_reject_other_roles(client):
    rid = create_via_api(client)
    for headers in (HOSPITAL_H, {"X-Test-User": "9"}):
        assert client.post(f"/api/requests/{rid}/approve", headers=headers).status_code == 403
        assert client.get("/api/requests/queue", headers=headers).status_code == 403
        assert client.get(f"/api/requests/{rid}/history", headers=headers).status_code == 403
    assert client.post(f"/api/requests/{rid}/approve").status_code == 401


def test_api_queue_rejects_unknown_status(client):
    assert client.get("/api/requests/queue?status=BOGUS", headers=STAFF_H).status_code == 422
