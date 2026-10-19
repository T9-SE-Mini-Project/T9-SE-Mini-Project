"""BLOOD-15 Submit Blood Request: schema, service and HTTP tests."""
from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from hospital_requests.models import NotFoundError, RequestRuleError
from hospital_requests.schemas import SubmitRequestIn
from support import (
    HOSPITAL_H, NOW, OTHER_HOSPITAL_USER, STAFF_H, USER, naive, submit, valid_payload,
)

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
    created = submit(service, patient_reference="P-123")
    assert created.id > 0
    assert created.status == "PENDING"
    assert (created.hospital_id, created.requested_by) == (1, 7)
    assert naive(created.created_at) == naive(NOW)


def test_quantity_above_limit_rejected(service):
    with pytest.raises(RequestRuleError) as exc:
        submit(service, quantity=11)
    assert exc.value.field == "quantity"
    assert service.list_requests(USER) == []


def test_quantity_at_limit_accepted(service):
    assert submit(service, quantity=10).quantity == 10


def test_required_by_in_past_rejected(service):
    with pytest.raises(RequestRuleError) as exc:
        submit(service, required_by=(NOW - timedelta(hours=1)).isoformat())
    assert exc.value.field == "required_by"


def test_required_by_in_future_accepted(service):
    when = NOW + timedelta(hours=6)
    assert naive(submit(service, required_by=when.isoformat()).required_by) == naive(when)


def test_hospital_only_sees_own_requests(service):
    mine = submit(service)
    theirs = service.submit_request(OTHER_HOSPITAL_USER, SubmitRequestIn(**valid_payload(blood_group="O-")))
    assert [r.id for r in service.list_requests(USER)] == [mine.id]
    assert service.get_request(USER, mine.id).id == mine.id
    with pytest.raises(NotFoundError):
        service.get_request(USER, theirs.id)


def test_get_missing_request_raises(service):
    with pytest.raises(NotFoundError):
        service.get_request(USER, 999)


# ---------- HTTP layer ----------


def test_api_submit_returns_201_and_pending(client):
    resp = client.post("/api/requests", json=valid_payload(), headers=HOSPITAL_H)
    assert resp.status_code == 201
    assert resp.json()["status"] == "PENDING" and resp.json()["hospital_id"] == 1


def test_api_bad_body_returns_422(client):
    assert client.post("/api/requests", json=valid_payload(quantity=0), headers=HOSPITAL_H).status_code == 422


def test_api_rule_error_returns_422(client):
    resp = client.post("/api/requests", json=valid_payload(quantity=11), headers=HOSPITAL_H)
    assert resp.status_code == 422
    assert resp.json()["detail"][0]["loc"] == ["body", "quantity"]


def test_api_requires_hospital_role(client):
    assert client.post("/api/requests", json=valid_payload()).status_code == 401
    assert client.post("/api/requests", json=valid_payload(), headers={"X-Test-User": "9"}).status_code == 403
    assert client.post("/api/requests", json=valid_payload(), headers=STAFF_H).status_code == 403


def test_api_other_hospitals_request_is_404(client):
    created = client.post("/api/requests", json=valid_payload(), headers={"X-Test-User": "8"}).json()
    assert client.get(f"/api/requests/{created['id']}", headers=HOSPITAL_H).status_code == 404
    assert client.get(f"/api/requests/{created['id']}", headers={"X-Test-User": "8"}).status_code == 200
    assert client.get("/api/requests", headers=HOSPITAL_H).json() == []
