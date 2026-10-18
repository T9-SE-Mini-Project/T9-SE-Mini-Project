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
from hospital_requests.models import NotFoundError, RequestRuleError  # noqa: E402
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
    users = {"7": USER, "8": OTHER_HOSPITAL_USER, "9": FakeUser(id=9, hospital_id=0, role="donor")}

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
