from datetime import date, datetime
from sqlalchemy import CheckConstraint, Date, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DonationRecord(Base):
    __tablename__ = "donation_history"
    __table_args__ = (
        UniqueConstraint("donation_id", name="uq_donation_history_donation_id"),
        CheckConstraint("quantity_ml > 0", name="ck_donation_history_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    donation_id: Mapped[str] = mapped_column(String(40), nullable=False)
    donor_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    donation_date: Mapped[date] = mapped_column(Date, nullable=False)
    blood_group: Mapped[str] = mapped_column(String(3), nullable=False)
    quantity_ml: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
