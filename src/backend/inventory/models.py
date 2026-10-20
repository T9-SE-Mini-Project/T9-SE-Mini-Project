from datetime import date
from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BloodBag(Base):
    __tablename__ = "blood_bags"
    __table_args__ = (UniqueConstraint("unit_id", name="uq_blood_bags_unit_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    unit_id: Mapped[str] = mapped_column(String(50), nullable=False)
    blood_group: Mapped[str] = mapped_column(String(3), nullable=False)
    component: Mapped[str] = mapped_column(String(20), nullable=False)
    collection_date: Mapped[date] = mapped_column(Date, nullable=False)
