"""Data-access code for the hospital_requests module.

Only touches the `blood_requests` table (never another module's tables).
Transaction boundary: each public method commits its own unit of work.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import BloodRequest, STATUS_PENDING
from .orm import BloodRequestRecord
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
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._session.refresh(record)
        return _to_domain(record)

    def get(self, request_id: int) -> Optional[BloodRequest]:
        record = self._session.get(BloodRequestRecord, request_id)
        return _to_domain(record) if record else None

    def list_for_hospital(self, hospital_id: int) -> list[BloodRequest]:
        stmt = (
            select(BloodRequestRecord)
            .where(BloodRequestRecord.hospital_id == hospital_id)
            .order_by(BloodRequestRecord.created_at.desc(), BloodRequestRecord.id.desc())
        )
        return [_to_domain(r) for r in self._session.scalars(stmt)]
