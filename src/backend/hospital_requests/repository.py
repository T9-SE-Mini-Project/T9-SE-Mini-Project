"""Data-access code for the hospital_requests module.

Only touches this module's own tables (`blood_requests`, `blood_request_events`).
Transaction boundary: each public method commits its own unit of work.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .models import BloodRequest, EVENT_SUBMITTED, RequestEvent, STATUS_PENDING
from .orm import BloodRequestRecord, RequestEventRecord
from .schemas import SubmitRequestIn


def _to_domain(record: BloodRequestRecord) -> BloodRequest:
    return BloodRequest(
        id=record.id,
        hospital_id=record.hospital_id,
        requested_by=record.requested_by,
        blood_group=record.blood_group,
        component=record.component,
        quantity=record.quantity,
        urgency=record.urgency,
        required_by=record.required_by,
        patient_reference=record.patient_reference,
        notes=record.notes,
        status=record.status,
        created_at=record.created_at,
    )


def _event_to_domain(record: RequestEventRecord) -> RequestEvent:
    return RequestEvent(
        id=record.id,
        request_id=record.request_id,
        action=record.action,
        actor_id=record.actor_id,
        note=record.note,
        created_at=record.created_at,
    )


class RequestRepository:
    def __init__(self, session: Session):
        self._session = session

    def create(
        self,
        *,
        hospital_id: int,
        requested_by: int,
        data: SubmitRequestIn,
        required_by: Optional[datetime],
        created_at: datetime,
    ) -> BloodRequest:
        record = BloodRequestRecord(
            hospital_id=hospital_id,
            requested_by=requested_by,
            blood_group=data.blood_group,
            component=data.component,
            quantity=data.quantity,
            urgency=data.urgency,
            required_by=required_by,
            patient_reference=data.patient_reference,
            notes=data.notes,
            status=STATUS_PENDING,
            created_at=created_at,
        )
        try:
            self._session.add(record)
            self._session.flush()  # assigns record.id
            self._session.add(
                RequestEventRecord(
                    request_id=record.id,
                    action=EVENT_SUBMITTED,
                    actor_id=requested_by,
                    note=None,
                    created_at=created_at,
                )
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._session.refresh(record)
        return _to_domain(record)

    def get(self, request_id: int) -> Optional[BloodRequest]:
        # populate_existing: never serve a stale copy after a status change.
        record = self._session.get(BloodRequestRecord, request_id, populate_existing=True)
        return _to_domain(record) if record else None

    def list_for_hospital(self, hospital_id: int) -> list[BloodRequest]:
        stmt = (
            select(BloodRequestRecord)
            .where(BloodRequestRecord.hospital_id == hospital_id)
            .order_by(BloodRequestRecord.created_at.desc(), BloodRequestRecord.id.desc())
        )
        return [_to_domain(r) for r in self._session.scalars(stmt)]

    def list_by_status(self, status: str) -> list[BloodRequest]:
        """Requests in one status, oldest first (first come, first served)."""
        stmt = (
            select(BloodRequestRecord)
            .where(BloodRequestRecord.status == status)
            .order_by(BloodRequestRecord.created_at.asc(), BloodRequestRecord.id.asc())
        )
        return [_to_domain(r) for r in self._session.scalars(stmt)]

    def transition(
        self,
        *,
        request_id: int,
        from_status: str,
        to_status: str,
        actor_id: int,
        note: Optional[str],
        at: datetime,
    ) -> bool:
        """Atomically change status and record who did it.

        The UPDATE only matches while the row is still in `from_status`, so if two staff
        act on the same request at once, exactly one succeeds and the other gets False.
        """
        try:
            result = self._session.execute(
                update(BloodRequestRecord)
                .where(BloodRequestRecord.id == request_id, BloodRequestRecord.status == from_status)
                .values(status=to_status)
            )
            if result.rowcount != 1:
                self._session.rollback()
                return False
            self._session.add(
                RequestEventRecord(
                    request_id=request_id,
                    action=to_status,
                    actor_id=actor_id,
                    note=note,
                    created_at=at,
                )
            )
            self._session.commit()
            return True
        except Exception:
            self._session.rollback()
            raise

    def list_events(self, request_id: int) -> list[RequestEvent]:
        stmt = (
            select(RequestEventRecord)
            .where(RequestEventRecord.request_id == request_id)
            .order_by(RequestEventRecord.id.asc())
        )
        return [_event_to_domain(r) for r in self._session.scalars(stmt)]
