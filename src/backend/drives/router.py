from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.backend.database.database import get_db
from src.backend.auth.dependencies import get_current_staff_user
from src.backend.drives import models, schemas

router = APIRouter(
    prefix="/api/drives",
    tags=["Drives"]
)

@router.post("/", response_model=schemas.DriveResponse, status_code=status.HTTP_201_CREATED)
def create_drive(
    drive_data: schemas.DriveCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_staff_user)
):
    # 1. Create the drive instance
    new_drive = models.Drive(
        name=drive_data.name,
        location=drive_data.location,
        date=drive_data.date
    )
    db.add(new_drive)
    db.commit()
    db.refresh(new_drive)

    # 2. Add all requested slots for this drive
    for slot_data in drive_data.slots:
        new_slot = models.Slot(
            drive_id=new_drive.id,
            start_time=slot_data.start_time,
            end_time=slot_data.end_time,
            capacity=slot_data.capacity,
            booked_count=0
        )
        db.add(new_slot)

    db.commit()
    db.refresh(new_drive)
    return new_drive

@router.post("/slots/{slot_id}/book", response_model=schemas.SlotBookingResponse)
def book_slot(
    slot_id: int,
    db: Session = Depends(get_db)
):
    # 1. Fetch slot from database
    slot = db.query(models.Slot).filter(models.Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot not found."
        )

    # 2. Capacity check (SRS rule)
    if slot.booked_count >= slot.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This slot is fully booked."
        )

    # 3. Update count and commit
    slot.booked_count += 1
    db.commit()
    db.refresh(slot)

    return {
        "message": "Slot booked successfully.",
        "slot_id": slot.id,
        "drive_id": slot.drive_id,
        "booked_count": slot.booked_count,
        "capacity": slot.capacity
    }