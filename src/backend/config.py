"""Application settings, read from environment variables (and `.env` in local development).

No secrets or environment-specific values are hard-coded. See `.env.example` for the
full list with explanations.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _list(name: str, default: str) -> tuple[str, ...]:
    raw = os.environ.get(name, default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class AppSettings:
    database_url: str = "sqlite:///./bbms.db"
    # Create missing tables at startup. Handy locally; turn off once Alembic owns the schema.
    create_tables: bool = True
    session_idle_timeout_seconds: int = 900
    # Origins allowed to call the API from a browser (the React + Vite dev server by default).
    cors_origins: tuple[str, ...] = field(default=("http://localhost:5173",))
    # How far ahead of a booked slot donors are reminded (BBS-F-042).
    reminder_window_hours: int = 24


def load_app_settings() -> AppSettings:
    try:
        from dotenv import load_dotenv
    except ImportError:  # python-dotenv is optional outside local development
        pass
    else:
        load_dotenv()

    return AppSettings(
        database_url=os.environ.get("DATABASE_URL", AppSettings.database_url),
        create_tables=_bool("BBMS_CREATE_TABLES", AppSettings.create_tables),
        session_idle_timeout_seconds=int(os.environ.get("SESSION_IDLE_TIMEOUT_SECONDS", "900")),
        cors_origins=_list("CORS_ORIGINS", "http://localhost:5173"),
        reminder_window_hours=int(os.environ.get("REMINDER_WINDOW_HOURS", "24")),
    )
