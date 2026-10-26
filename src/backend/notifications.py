"""Notification delivery: signup OTPs (BLOOD-7) and drive slot reminders (BBS-F-042).

Modules depend on the small Protocols they need (`auth.signup.OTPSender`,
`drives.service.ReminderSender`), not on this file, so a real SMS/email provider can be
dropped in later without touching them. `LoggingNotifier` is the stand-in until then.
"""
from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger("bbms.notifications")


class LoggingNotifier:
    """DEVELOPMENT ONLY: writes messages to the server log instead of sending them.

    It logs OTP codes so a developer can finish signup locally. Never use it in
    production: OTPs must only reach the user (see `auth.signup.OTPSender`).
    """

    def send_otp(self, email: str, code: str) -> None:
        logger.warning("[DEV] Signup code for %s: %s", email, code)

    def send_slot_reminder(self, email: str, drive_name: str, location: str, start_time: datetime) -> None:
        logger.info(
            "[DEV] Reminder to %s: your slot at %s (%s) starts %s",
            email, drive_name, location, start_time.isoformat(),
        )
