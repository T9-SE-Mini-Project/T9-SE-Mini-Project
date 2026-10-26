"""Shared SQLAlchemy base and session handling for every module.

All ORM models inherit from the one `Base` below, so every table lives in a single
`Base.metadata`. That lets tables reference each other with foreign keys (for example
`donor_profiles.donor_id -> auth_users.id`) and lets the app or Alembic create the
whole schema in one step.

Modules keep their old names as aliases (`AuthBase`, `donor.models.Base`, ...) so code
and tests that import them keep working.
"""
from __future__ import annotations

from typing import Callable, Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """Declarative base shared by every table in the system."""


def create_db_engine(database_url: str) -> Engine:
    """Build an engine for `database_url` (PostgreSQL in production, SQLite locally)."""
    if database_url.startswith("sqlite"):
        # FastAPI runs sync endpoints in a thread pool, so SQLite must allow that.
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in database_url or database_url in ("sqlite://", "sqlite+pysqlite://"):
            # One shared connection, otherwise every session sees its own empty database.
            kwargs["poolclass"] = StaticPool
        return create_engine(database_url, **kwargs)
    return create_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def make_get_session(session_factory: sessionmaker[Session]) -> Callable[[], Iterator[Session]]:
    """FastAPI dependency giving each request its own session, closed afterwards."""

    def get_session() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    return get_session


def import_all_models() -> None:
    """Import every ORM module so all tables are registered on `Base.metadata`."""
    from .auth import orm as _auth  # noqa: F401
    from .donor import models as _donor  # noqa: F401
    from .drives import models as _drives  # noqa: F401
    from .hospital_requests import orm as _requests  # noqa: F401
    from .inventory import models as _inventory  # noqa: F401


def create_all_tables(engine: Engine) -> None:
    """Create any missing tables. For local development; production should use migrations."""
    import_all_models()
    Base.metadata.create_all(engine)
