"""Pydantic request/response schemas for /api/drives.

`datetime` is imported as a module (`dt`) because a field named `date` would otherwise
hide the `date` type inside the class body.
"""
from __future__ import annotations

import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SlotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_time: dt.datetime
    end_time: dt.datetime
    capacity: int = Field(default=10, gt=0, le=500)

    @model_validator(mode="after")
    def _end_after_start(self) -> "SlotCreate":
        if self.end_time <= self.start_time:
            raise ValueError("A slot must end after it starts.")
        return self


class DriveCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=3, max_length=100)
    location: str = Field(min_length=3, max_length=200)
    date: dt.date
    # AC-040: a drive cannot be created without at least one slot.
    slots: List[SlotCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def _slots_on_drive_date(self) -> "DriveCreate":
        for slot in self.slots:
            if slot.start_time.date() != self.date:
                raise ValueError("Every slot must start on the drive date.")
        return self


class SlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    drive_id: int
    start_time: dt.datetime
    end_time: dt.datetime
    capacity: int
    booked_count: int


class DriveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    date: dt.date
    slots: List[SlotResponse]


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slot_id: int
    drive_id: int
    donor_id: int
    booked_at: dt.datetime
    reminder_sent_at: Optional[dt.datetime]
    slot: SlotResponse


class ReminderResponse(BaseModel):
    message: str
    reminders_sent: int
    booking_ids: List[int]
