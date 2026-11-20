"""System test harness: a real BBMS server process, driven over HTTP.

Unlike the integration tests (FastAPI TestClient, in-process), each system test starts
`uvicorn src.backend.main:app` as a separate process on a free port with its own empty
SQLite file, and talks to it with a plain HTTP client, the way the React frontend does.

The first admin is created the way `python -m src.backend.cli create-admin` does it.
Every other account goes through the product itself: the admin creates staff and
hospital accounts over the API, donors sign up and verify with the OTP that the
development notifier writes to the server log.
"""
from __future__ import annotations

import os
import re
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from src.backend.auth.accounts import create_account
from src.backend.database import create_all_tables, create_db_engine, create_session_factory

REPO_ROOT = Path(__file__).resolve().parents[2]
PASSWORD = "SystemTest123!"
ADMIN_EMAIL = "sysadmin@example.com"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class BBMS:
    """One running server plus small helpers for the steps every scenario repeats."""

    def __init__(self, base_url: str, db_path: Path, log_path: Path):
        self.base_url = base_url
        self.db_path = db_path
        self.log_path = log_path
        self.http = httpx.Client(base_url=base_url, timeout=15)
        self._emails = 0

    # ----- accounts -----

    def login(self, email: str, password: str = PASSWORD) -> dict:
        response = self.http.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def admin(self) -> dict:
        return self.login(ADMIN_EMAIL)

    def _next_email(self, prefix: str) -> str:
        self._emails += 1
        return f"{prefix}{self._emails}@example.com"

    def new_account(self, role: str, hospital_id: int | None = None) -> tuple[str, dict]:
        """Admin creates a staff / hospital / admin account. Returns (email, auth headers)."""
        email = self._next_email(role)
        body = {"email": email, "password": PASSWORD, "role": role}
        if hospital_id is not None:
            body["hospital_id"] = hospital_id
        response = self.http.post("/api/admin/accounts", headers=self.admin(), json=body)
        assert response.status_code == 201, response.text
        return email, self.login(email)

    def staff(self) -> dict:
        return self.new_account("blood_bank_staff")[1]

    def hospital(self, hospital_id: int = 1) -> dict:
        return self.new_account("hospital_rep", hospital_id)[1]

    def otp_for(self, email: str) -> str:
        """The signup code the server logged for `email` (development notifier)."""
        pattern = re.compile(rf"Signup code for {re.escape(email)}: (\d{{6}})")
        deadline = time.time() + 5
        while time.time() < deadline:
            codes = pattern.findall(self.log_path.read_text(errors="replace"))
            if codes:
                return codes[-1]
            time.sleep(0.05)
        raise AssertionError(f"No signup code for {email} in the server log")

    def new_donor(self, profile: dict | None = None) -> tuple[str, dict]:
        """Donor signs up, verifies the OTP and (optionally) saves a profile."""
        email = self._next_email("donor")
        response = self.http.post("/api/auth/signup", json={"email": email, "password": PASSWORD})
        assert response.status_code == 202, response.text
        response = self.http.post("/api/auth/signup/verify", json={"email": email, "code": self.otp_for(email)})
        assert response.status_code == 200, response.text
        headers = self.login(email)
        if profile is not None:
            response = self.http.post("/api/donors/profile", headers=headers, json=profile)
            assert response.status_code == 201, response.text
        return email, headers

    def user_id(self, headers: dict) -> int:
        return self.http.get("/api/auth/me", headers=headers).json()["id"]

    # ----- inventory and requests -----

    def log_bag(self, staff: dict, blood_group: str, component: str = "RBC", days_ago: int = 1) -> dict:
        from datetime import date, timedelta

        response = self.http.post("/api/inventory/bags", headers=staff, json={
            "blood_group": blood_group,
            "component": component,
            "collection_date": (date.today() - timedelta(days=days_ago)).isoformat(),
        })
        assert response.status_code == 201, response.text
        return response.json()

    def submit_request(self, hospital: dict, blood_group: str, quantity: int, component: str = "RBC") -> int:
        response = self.http.post("/api/requests", headers=hospital, json={
            "blood_group": blood_group, "component": component, "quantity": quantity, "urgency": "urgent",
        })
        assert response.status_code == 201, response.text
        return response.json()["id"]

    # ----- database inspection (for "DB check" acceptance criteria) -----

    def sql(self, query: str, params: tuple = ()) -> list[tuple]:
        connection = sqlite3.connect(self.db_path)
        try:
            rows = connection.execute(query, params).fetchall()
            connection.commit()
            return rows
        finally:
            connection.close()


@pytest.fixture
def start_bbms(tmp_path):
    """Factory: start a server with optional extra environment variables."""
    running: list[tuple[subprocess.Popen, BBMS, object]] = []

    def start(**env_overrides: str) -> BBMS:
        index = len(running)
        db_path = tmp_path / f"bbms_system_{index}.db"
        log_path = tmp_path / f"server_{index}.log"
        database_url = f"sqlite:///{db_path}"

        engine = create_db_engine(database_url)
        create_all_tables(engine)
        with create_session_factory(engine)() as db:
            create_account(db, ADMIN_EMAIL, PASSWORD, "admin")
        engine.dispose()

        port = _free_port()
        env = {**os.environ, "DATABASE_URL": database_url, "BBMS_CREATE_TABLES": "true", **env_overrides}
        log_file = open(log_path, "w")
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.backend.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=REPO_ROOT, env=env, stdout=log_file, stderr=subprocess.STDOUT,
        )
        system = BBMS(f"http://127.0.0.1:{port}", db_path, log_path)
        running.append((process, system, log_file))

        deadline = time.time() + 30
        while True:
            if process.poll() is not None:
                raise RuntimeError("BBMS server exited during startup:\n" + log_path.read_text())
            try:
                if system.http.get("/api/health").status_code == 200:
                    return system
            except httpx.TransportError:
                pass
            if time.time() > deadline:
                raise RuntimeError("BBMS server did not start:\n" + log_path.read_text())
            time.sleep(0.1)

    yield start

    for process, system, log_file in running:
        system.http.close()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log_file.close()


@pytest.fixture
def bbms(start_bbms) -> BBMS:
    return start_bbms()
