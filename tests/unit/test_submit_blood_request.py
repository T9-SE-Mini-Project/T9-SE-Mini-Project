"""Unit/API tests for BLOOD-15 Submit Blood Request (FastAPI + SQLAlchemy)."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "backend"))

from hospital_requests.config import Settings  # noqa: E402
from hospital_requests.models import InvalidTransitionError, NotFoundError, RequestRuleError  # noqa: E402
from hospital_requests.orm import Base  # noqa: E402
from hospital_requests.repository import RequestRepository  # noqa: E402
from hospital_requests.routes import create_router  # noqa: E402
from hospital_requests.schemas import SubmitRequestIn  # noqa: E402
from hospital_requests.service import RequestService  # noqa: E402

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class FakeUser:
    id: int
    hospital_id: int
    role: str = "hospital_rep"


USER = FakeUser(id=7, hospital_id=1)
OTHER_HOSPITAL_USER = FakeUser(id=8, hospital_id=2)
STAFF = FakeUser(id=20, hospital_id=0, role="blood_bank_staff")
OTHER_STAFF = FakeUser(id=21, hospital_id=0, role="blood_bank_staff")


def valid_payload(**overrides) -> dict:
    payload = {"blood_group": "A+", "component": "RBC", "quantity": 2, "urgency": "urgent"}
    payload.update(overrides)
    return payload


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def service(session_factory):
    session = session_factory()
    yield RequestService(RequestRepository(session), Settings(max_units_per_request=10), clock=lambda: NOW)
    session.close()


def naive(dt: datetime) -> datetime:
    """SQLite drops tzinfo; PostgreSQL keeps it. Compare on the wall-clock value."""
    return dt.replace(tzinfo=None)


# ---------- schema validation (shape/type rules) ----------

@pytest.mark.parametrize(
    "field,value",
    [
        ("blood_group", "C+"),
        ("blood_group", None),
        ("component", "Water"),
        ("quantity", 0),
        ("quantity", -1),
        ("quantity", 2.5),
        ("quantity", "3"),
        ("quantity", True),
        ("urgency", "asap"),
        ("required_by", "not-a-date"),
        ("notes", "x" * 501),
        ("patient_reference", "x" * 51),
    ],
)
def test_schema_rejects_bad_field(field, value):
    with pytest.raises(ValidationError) as exc:
        SubmitRequestIn(**valid_payload(**{field: value}))
    assert field in {err["loc"][0] for err in exc.value.errors()}


def test_schema_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        SubmitRequestIn(**valid_payload(status="APPROVED"))


def test_schema_reports_all_errors_and_defaults():
    with pytest.raises(ValidationError) as exc:
        SubmitRequestIn(quantity=0)
    assert {"blood_group", "component", "quantity"} <= {e["loc"][0] for e in exc.value.errors()}
    assert SubmitRequestIn(**{k: v for k, v in valid_payload().items() if k != "urgency"}).urgency == "routine"


def test_schema_trims_and_blanks_text_fields():
    body = SubmitRequestIn(**valid_payload(patient_reference="  P-123  ", notes="   "))
    assert body.patient_reference == "P-123" and body.notes is None


# ---------- service (business rules) ----------

def test_submit_valid_request_is_pending(service):
    created = service.submit_request(USER, SubmitRequestIn(**valid_payload(patient_reference="P-123")))
    assert created.id > 0
    assert created.status == "PENDING"
    assert (created.hospital_id, created.requested_by) == (1, 7)
    assert naive(created.created_at) == naive(NOW)


def test_quantity_above_limit_rejected(service):
    with pytest.raises(RequestRuleError) as exc:
        service.submit_request(USER, SubmitRequestIn(**valid_payload(quantity=11)))
    assert exc.value.field == "quantity"
    assert service.list_requests(USER) == []


def test_quantity_at_limit_accepted(service):
    assert service.submit_request(USER, SubmitRequestIn(**valid_payload(quantity=10))).quantity == 10


def test_required_by_in_past_rejected(service):
    past = (NOW - timedelta(hours=1)).isoformat()
    with pytest.raises(RequestRuleError) as exc:
        service.submit_request(USER, SubmitRequestIn(**valid_payload(required_by=past)))
    assert exc.value.field == "required_by"


def test_required_by_in_future_accepted(service):
    when = NOW + timedelta(hours=6)
    created = service.submit_request(USER, SubmitRequestIn(**valid_payload(required_by=when.isoformat())))
    assert naive(created.required_by) == naive(when)


def test_hospital_only_sees_own_requests(service):
    mine = service.submit_request(USER, SubmitRequestIn(**valid_payload()))
    theirs = service.submit_request(OTHER_HOSPITAL_USER, SubmitRequestIn(**valid_payload(blood_group="O-")))
    assert [r.id for r in service.list_requests(USER)] == [mine.id]
    assert service.get_request(USER, mine.id).id == mine.id
    with pytest.raises(NotFoundError):
        service.get_request(USER, theirs.id)


def test_get_missing_request_raises(service):
    with pytest.raises(NotFoundError):
        service.get_request(USER, 999)


# ---------- HTTP layer ----------

@pytest.fixture
def client(session_factory):
    users = {
        "7": USER,
        "8": OTHER_HOSPITAL_USER,
        "9": FakeUser(id=9, hospital_id=0, role="donor"),
        "20": STAFF,
    }

    def fake_require_role(role: str):
        def dependency(x_test_user: str | None = Header(default=None)):
            if x_test_user is None:
                raise HTTPException(status_code=401)
            user = users[x_test_user]
            if user.role != role:
                raise HTTPException(status_code=403)
            return user

        return dependency

    def get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app = FastAPI()
    app.include_router(create_router(get_session, fake_require_role, Settings(max_units_per_request=10)))
    return TestClient(app)


def test_api_submit_returns_201_and_pending(client):
    resp = client.post("/api/requests", json=valid_payload(), headers={"X-Test-User": "7"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "PENDING" and resp.json()["hospital_id"] == 1


def test_api_bad_body_returns_422(client):
    resp = client.post("/api/requests", json=valid_payload(quantity=0), headers={"X-Test-User": "7"})
    assert resp.status_code == 422


def test_api_rule_error_returns_422(client):
    resp = client.post("/api/requests", json=valid_payload(quantity=11), headers={"X-Test-User": "7"})
    assert resp.status_code == 422
    assert resp.json()["detail"][0]["loc"] == ["body", "quantity"]


def test_api_requires_hospital_role(client):
    assert client.post("/api/requests", json=valid_payload()).status_code == 401
    assert client.post("/api/requests", json=valid_payload(), headers={"X-Test-User": "9"}).status_code == 403


def test_api_other_hospitals_request_is_404(client):
    created = client.post("/api/requests", json=valid_payload(), headers={"X-Test-User": "8"}).json()
    assert client.get(f"/api/requests/{created['id']}", headers={"X-Test-User": "7"}).status_code == 404
    assert client.get(f"/api/requests/{created['id']}", headers={"X-Test-User": "8"}).status_code == 200
    assert client.get("/api/requests", headers={"X-Test-User": "7"}).json() == []


# ---------- BLOOD-17: approve, reject, dispatch (service) ----------

def submit(service, **overrides):
    return service.submit_request(USER, SubmitRequestIn(**valid_payload(**overrides)))


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
    assert service.get_request(USER, req.id).status == "PENDING"


@pytest.mark.parametrize("first,second", [("approve", "approve"), ("reject", "approve"), ("approve", "reject")])
def test_cannot_decide_a_request_twice(service, first, second):
    req = submit(service)
    act = {"approve": lambda: service.approve(STAFF, req.id), "reject": lambda: service.reject(STAFF, req.id, "no")}
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


def test_transition_only_applies_from_expected_status(session_factory):
    """Simulates two staff racing: the second, stale update must lose and leave no history."""
    repo = RequestRepository(session_factory())
    created = repo.create(
        hospital_id=1, requested_by=7, data=SubmitRequestIn(**valid_payload()), required_by=None, created_at=NOW
    )
    args = dict(request_id=created.id, from_status="PENDING", at=NOW)
    assert repo.transition(to_status="APPROVED", actor_id=20, note=None, **args) is True
    assert repo.transition(to_status="REJECTED", actor_id=21, note="late", **args) is False
    assert repo.get(created.id).status == "APPROVED"
    assert [e.action for e in repo.list_events(created.id)] == ["SUBMITTED", "APPROVED"]


# ---------- BLOOD-17: HTTP layer ----------

STAFF_H = {"X-Test-User": "20"}
HOSPITAL_H = {"X-Test-User": "7"}


def create_via_api(client) -> int:
    return client.post("/api/requests", json=valid_payload(), headers=HOSPITAL_H).json()["id"]


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


def test_api_staff_cannot_use_hospital_endpoints(client):
    assert client.post("/api/requests", json=valid_payload(), headers=STAFF_H).status_code == 403


def test_api_queue_rejects_unknown_status(client):
    assert client.get("/api/requests/queue?status=BOGUS", headers=STAFF_H).status_code == 422
