"""Shared pytest fixtures for the hospital_requests tests."""
from __future__ import annotations

import support  # noqa: F401  (also puts src/backend on sys.path)
from support import NOW, OTHER_HOSPITAL_USER, SETTINGS, STAFF, USER, FakeInventory, FakeUser, default_units

import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from hospital_requests.orm import Base
from hospital_requests.repository import RequestRepository
from hospital_requests.routes import create_router
from hospital_requests.service import RequestService


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def repo(session_factory):
    session = session_factory()
    yield RequestRepository(session)
    session.close()


@pytest.fixture
def inventory():
    return FakeInventory(default_units())


@pytest.fixture
def service(repo, inventory):
    return RequestService(repo, inventory, SETTINGS, clock=lambda: NOW)


@pytest.fixture
def client(session_factory, inventory):
    users = {
        "7": USER,
        "8": OTHER_HOSPITAL_USER,
        "9": FakeUser(id=9, hospital_id=0, role="donor"),
        "20": STAFF,
    }

    def fake_require_role(role: str):
        def dependency(x_test_user: str | None = Header(default=None)):
            if x_test_user is None:
                raise HTTPException(status_code=401)
            user = users[x_test_user]
            if user.role != role:
                raise HTTPException(status_code=403)
            return user

        return dependency

    def get_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app = FastAPI()
    app.include_router(create_router(get_session, fake_require_role, inventory, SETTINGS))
    return TestClient(app)
