"""BLOOD-16 / BBS-F-032: inventory's CrossMatchInterface implementation."""
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.backend.database import Base
from src.backend.inventory.cross_match import InventoryCrossMatch
from src.backend.inventory.models import BloodBag
from src.backend.inventory.service import add_blood_bag, expire_blood_units


@pytest.fixture
def factory():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def stock(factory):
    def add(group, component="RBC", collected=None):
        with factory() as db:
            return add_blood_bag(db, group, component, collected or date.today()).unit_id
    return add


def status_of(factory, unit_id):
    with factory() as db:
        return db.scalar(select(BloodBag).where(BloodBag.unit_id == unit_id))


def test_find_prefers_exact_group_then_soonest_expiry(factory, stock):
    o_neg = stock("O-")
    a_pos_old = stock("A+", collected=date.today() - timedelta(days=10))
    a_pos_new = stock("A+")
    stock("B-")  # incompatible with A+
    stock("A+", component="Plasma")  # wrong component
    units = InventoryCrossMatch(factory).find_compatible_units("A+", "RBC", 5)
    assert [u.unit_id for u in units] == [a_pos_old, a_pos_new, o_neg]


def test_find_respects_quantity_and_skips_expired(factory, stock):
    stock("A+", component="Platelets", collected=date.today() - timedelta(days=6))  # expired
    fresh = stock("A+", component="Platelets")
    stock("A+", component="Platelets")
    units = InventoryCrossMatch(factory).find_compatible_units("A+", "Platelets", 1)
    assert [u.unit_id for u in units] == [fresh]


def test_allocate_is_all_or_nothing(factory, stock):
    cm = InventoryCrossMatch(factory)
    first, second = stock("O-"), stock("O-")
    assert cm.allocate_units([first], request_id=1)
    # `first` is taken, so allocating both for another request must change nothing.
    assert not cm.allocate_units([first, second], request_id=2)
    assert status_of(factory, second).status == "AVAILABLE"
    bag = status_of(factory, first)
    assert (bag.status, bag.allocated_request_id) == ("ALLOCATED", 1)


def test_only_one_of_two_competing_allocations_wins(factory, stock):
    """BBS-NF-005: the same unit can never go to two requests."""
    cm = InventoryCrossMatch(factory)
    unit = stock("AB+")
    assert [cm.allocate_units([unit], 1), cm.allocate_units([unit], 2)] == [True, False]


def test_release_only_touches_the_owning_request(factory, stock):
    cm = InventoryCrossMatch(factory)
    unit = stock("A-")
    cm.allocate_units([unit], 1)
    cm.release_units([unit], request_id=2)
    assert status_of(factory, unit).status == "ALLOCATED"
    cm.release_units([unit], request_id=1)
    cm.release_units([unit], request_id=1)  # idempotent
    bag = status_of(factory, unit)
    assert (bag.status, bag.allocated_request_id) == ("AVAILABLE", None)


def test_dispatch_marks_units_and_is_safe_to_retry(factory, stock):
    cm = InventoryCrossMatch(factory)
    units = [stock("B+"), stock("B+")]
    cm.allocate_units(units, 3)
    assert not cm.dispatch_units(units, request_id=4)
    assert cm.dispatch_units(units, request_id=3)
    assert cm.dispatch_units(units, request_id=3)
    assert {status_of(factory, u).status for u in units} == {"DISPATCHED"}


def test_expired_allocated_unit_cannot_be_dispatched(factory, stock):
    cm = InventoryCrossMatch(factory)
    unit = stock("O+", component="Platelets")
    cm.allocate_units([unit], 5)
    expiry = status_of(factory, unit).expiry_date
    with factory() as db:
        assert expire_blood_units(db, actor_id=1, today=expiry) == 1
    assert status_of(factory, unit).status == "EXPIRED"
    assert not cm.dispatch_units([unit], 5)
