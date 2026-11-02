from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.backend.database import Base, import_all_models
from src.backend.inventory.low_stock import get_low_stock_alerts
from src.backend.inventory.models import BloodBag


@pytest.fixture
def db():
    import_all_models()
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def bag(db, group="O+", component="RBC", days_left=10, status="AVAILABLE"):
    bag = BloodBag(
        unit_id=f"BAG-{len(db.query(BloodBag).all()) + 1}",
        blood_group=group,
        component=component,
        collection_date=date.today() - timedelta(days=1),
        expiry_date=date.today() + timedelta(days=days_left),
        status=status,
    )
    db.add(bag)
    db.commit()


def get_item(alerts, group="O+", component="RBC"):
    return next((a for a in alerts if a["blood_group"] == group and a["component"] == component), None)


def test_empty_stock_reports_zero(db):
    alerts = get_low_stock_alerts(db)
    item = get_item(alerts)
    assert item["available_units"] == 0
    assert item["level"] == "OUT_OF_STOCK"


def test_one_available_bag_is_low(db):
    bag(db)
    item = get_item(get_low_stock_alerts(db))
    assert item["available_units"] == 1
    assert item["level"] == "LOW_STOCK"


def test_threshold_boundary(db):
    for _ in range(3):
        bag(db)
    assert get_item(get_low_stock_alerts(db, threshold=2)) is None
    assert get_item(get_low_stock_alerts(db, threshold=3))["available_units"] == 3


def test_expired_not_counted(db):
    bag(db, days_left=0)
    assert get_item(get_low_stock_alerts(db))["available_units"] == 0


def test_allocated_not_counted(db):
    bag(db, status="ALLOCATED")
    assert get_item(get_low_stock_alerts(db))["available_units"] == 0


def test_dispatched_not_counted(db):
    bag(db, status="DISPATCHED")
    assert get_item(get_low_stock_alerts(db))["available_units"] == 0


def test_groups_and_components_separated(db):
    bag(db, "A+", "RBC")
    bag(db, "A+", "Plasma")
    assert get_item(get_low_stock_alerts(db), "A+", "RBC")["available_units"] == 1
    assert get_item(get_low_stock_alerts(db), "A+", "Plasma")["available_units"] == 1
    assert get_item(get_low_stock_alerts(db), "A-", "RBC")["available_units"] == 0


@pytest.mark.parametrize("threshold", [-1, None, True, 1.5, "5"])
def test_invalid_threshold_rejected(db, threshold):
    with pytest.raises(ValueError):
        get_low_stock_alerts(db, threshold)
