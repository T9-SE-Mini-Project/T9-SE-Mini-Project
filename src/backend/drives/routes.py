"""REST routes for /api/drives (BBS-F-040, BBS-F-041, BBS-F-042).

The SRS "Drive Coordinator" is not a separate login role, so blood bank staff and
admins coordinate drives. Donors view upcoming drives and book slots.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from . import service
from .schemas import BookingResponse, DriveCreate, DriveResponse, ReminderResponse

COORDINATOR_ROLES = ("blood_bank_staff", "admin")


def create_drives_router(get_session, require_role, reminder_sender: service.ReminderSender, reminder_window_hours: int = 24):
    router = APIRouter(prefix="/api/drives", tags=["drives"])
    coordinator = require_role(*COORDINATOR_ROLES)
    donor_only = require_role("donor")
    any_viewer = require_role("donor", *COORDINATOR_ROLES)

    @router.post("", response_model=DriveResponse, status_code=status.HTTP_201_CREATED)
    def create_drive(payload: DriveCreate, user=Depends(coordinator), db=Depends(get_session)):
        return service.create_drive(db, payload, created_by=user.id)

    @router.get("", response_model=list[DriveResponse])
    def upcoming_drives(user=Depends(any_viewer), db=Depends(get_session)):
        return service.list_upcoming_drives(db)

    @router.post(
        "/slots/{slot_id}/book",
        response_model=BookingResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def book_slot(slot_id: int, donor=Depends(donor_only), db=Depends(get_session)):
        try:
            return service.book_slot(db, slot_id, donor.id)
        except service.BookingError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    @router.get("/bookings/me", response_model=list[BookingResponse])
    def my_bookings(donor=Depends(donor_only), db=Depends(get_session)):
        return service.list_bookings_for_donor(db, donor.id)

    @router.post("/reminders/send", response_model=ReminderResponse)
    def send_reminders(user=Depends(coordinator), db=Depends(get_session)):
        """Send reminders that are due now. Can also be scheduled: `python -m src.backend.cli send-reminders`."""
        run = service.send_due_reminders(db, reminder_sender, timedelta(hours=reminder_window_hours))
        return ReminderResponse(
            message=f"Sent {len(run.booking_ids)} reminder(s).",
            reminders_sent=len(run.booking_ids),
            booking_ids=run.booking_ids,
        )

    return router
