"""BLOOD-7: OTP expiry, resend, attempt limit, and delivery failure."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.backend.auth.orm import AuthBase, SignupOTP
from src.backend.auth.repository import AccountRepository
from src.backend.auth.service import AuthService, AuthenticationError
from src.backend.auth.signup import SignupError, SignupService


class FakeSender:
    def __init__(self, fail=False):
        self.codes = []
        self.fail = fail

    def send_otp(self, email, code):
        if self.fail:
            raise RuntimeError("Notification service unavailable")
        self.codes.append(code)


@pytest.fixture
def database():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    AuthBase.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_expired_code_can_be_replaced_and_old_code_fails(database, monkeypatch):
    codes = iter(("123456", "654321"))
    monkeypatch.setattr(
        "src.backend.auth.signup.generate_otp", lambda: next(codes)
    )
    now = [1000]
    sender = FakeSender()
    service = SignupService(database, sender, clock=lambda: now[0])
    service.register_donor("donor@example.com", "ExamplePassword123!")

    now[0] = 1300
    with pytest.raises(SignupError):
        service.verify_signup("donor@example.com", "123456")

    service.resend_otp("donor@example.com")
    assert sender.codes == ["123456", "654321"]

    with pytest.raises(SignupError):
        service.verify_signup("donor@example.com", "123456")

    service.verify_signup("donor@example.com", "654321")
    assert AuthService(AccountRepository(database)).authenticate(
        "donor@example.com", "ExamplePassword123!"
    ).role == "donor"


def test_five_wrong_codes_block_verification(database, monkeypatch):
    monkeypatch.setattr(
        "src.backend.auth.signup.generate_otp", lambda: "123456"
    )
    service = SignupService(database, FakeSender())
    service.register_donor("donor@example.com", "ExamplePassword123!")

    for _ in range(5):
        with pytest.raises(SignupError):
            service.verify_signup("donor@example.com", "000000")

    with pytest.raises(SignupError, match="Too many verification attempts"):
        service.verify_signup("donor@example.com", "123456")

    account = AccountRepository(database).get_by_email("donor@example.com")
    assert not account.is_verified
    assert database.get(SignupOTP, account.id).attempts == 5

    with pytest.raises(AuthenticationError):
        AuthService(AccountRepository(database)).authenticate(
            "donor@example.com", "ExamplePassword123!"
        )


def test_delivery_failure_does_not_create_account(database):
    service = SignupService(database, FakeSender(fail=True))

    with pytest.raises(RuntimeError, match="Notification service unavailable"):
        service.register_donor("donor@example.com", "ExamplePassword123!")

    assert AccountRepository(database).get_by_email("donor@example.com") is None
