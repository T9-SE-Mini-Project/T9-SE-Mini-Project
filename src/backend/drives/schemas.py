from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import List

class SlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    capacity: int = Field(default=10, gt=0)

class SlotResponse(SlotCreate):
    id: int
    drive_id: int
    booked_count: int

    class Config:
        from_attributes = True

class DriveCreate(BaseModel):
    name: str = Field(..., min_length=3)
    location: str = Field(..., min_length=3)
    date: date
    slots: List[SlotCreate]

    @field_validator('slots')
    @classmethod
    def validate_slots(cls, v):
        if not v or len(v) == 0:
            raise ValueError("A drive must have at least one slot.")
        return v

class DriveResponse(BaseModel):
    id: int
    name: str
    location: str
    date: date
    slots: List[SlotResponse]

    class Config:
        from_attributes = True