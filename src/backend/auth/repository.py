"""Account lookups using a database session supplied by the application."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .orm import Account


def normalize_email(email: str) -> str:
    """Use the same email representation for account creation and login."""
    return email.strip().lower()


class AccountRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_email(self, email: str) -> Account | None:
        statement = select(Account).where(
            Account.email == normalize_email(email)
        )
        return self.session.scalar(statement)

    def get_by_id(self, user_id: int) -> Account | None:
        return self.session.get(Account, user_id)
