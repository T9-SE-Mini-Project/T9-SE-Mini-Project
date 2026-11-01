"""BBMS FastAPI application: wires every module together.

Each feature module exposes a router factory that receives its dependencies (database
session, auth guards, collaborators) instead of importing them. This file is the only
place that knows about all of them (composition root), which keeps the modules
independent and easy to test with fakes.

Run locally:
    uvicorn src.backend.main:app --reload
API docs are then served at http://127.0.0.1:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth.admin_routes import create_admin_router
from .auth.dependencies import create_auth_dependencies
from .auth.routes import create_router as create_auth_router
from .auth.signup import OTPSender
from .auth.signup_routes import create_signup_router
from .config import AppSettings, load_app_settings
from .database import create_all_tables, create_db_engine, create_session_factory, make_get_session
from .donor.profile_routes import create_profile_router
from .donor.routes import create_donor_router
from .drives.routes import create_drives_router
from .drives.service import ReminderSender
from .hospital_requests import create_router as create_requests_router
from .hospital_requests import load_settings as load_request_settings
from .inventory.cross_match import InventoryCrossMatch
from .inventory.routes import create_inventory_router
from .notifications import LoggingNotifier


def create_app(
    settings: Optional[AppSettings] = None,
    otp_sender: Optional[OTPSender] = None,
    reminder_sender: Optional[ReminderSender] = None,
) -> FastAPI:
    """Build the app. Tests and other environments can pass their own settings and senders."""
    settings = settings or load_app_settings()
    notifier = LoggingNotifier()
    otp_sender = otp_sender or notifier
    reminder_sender = reminder_sender or notifier

    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    get_session = make_get_session(session_factory)
    get_current_user, require_role = create_auth_dependencies(
        get_session, settings.session_idle_timeout_seconds
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if settings.create_tables:
            create_all_tables(engine)
        yield
        engine.dispose()

    app = FastAPI(
        title="Blood Bank & Donation Management System",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,  # bearer tokens, no cookies
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Auth and accounts (BLOOD-6, BLOOD-7, BLOOD-8)
    app.include_router(create_auth_router(get_session, get_current_user, settings.session_idle_timeout_seconds))
    app.include_router(create_signup_router(get_session, otp_sender))
    app.include_router(create_admin_router(get_session, require_role))
    # Donors (BLOOD-9, BLOOD-10)
    app.include_router(create_profile_router(get_session, require_role))
    app.include_router(create_donor_router(get_session, require_role))
    # Inventory (BLOOD-12, BLOOD-13, BLOOD-14)
    app.include_router(create_inventory_router(get_session, require_role))
    # Hospital requests (BLOOD-15, BLOOD-16, BLOOD-17)
    app.include_router(
        create_requests_router(get_session, require_role, InventoryCrossMatch(session_factory), load_request_settings())
    )
    # Drives (BBS-F-040, BBS-F-041, BBS-F-042)
    app.include_router(
        create_drives_router(get_session, require_role, reminder_sender, settings.reminder_window_hours)
    )

    @app.get("/api/health", tags=["health"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
