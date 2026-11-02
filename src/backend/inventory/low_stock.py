from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..blood import BLOOD_GROUPS, COMPONENTS
from .models import BloodBag, STATUS_AVAILABLE


def get_low_stock_alerts(db: Session, threshold: int = 5, today: date | None = None) -> list[dict]:
    if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 0:
        raise ValueError("Threshold must be a non-negative integer")
    current_date = today or date.today()
    rows = db.execute(
        select(BloodBag.blood_group, BloodBag.component, func.count(BloodBag.id))
        .where(BloodBag.status == STATUS_AVAILABLE, BloodBag.expiry_date > current_date)
        .group_by(BloodBag.blood_group, BloodBag.component)
    ).all()
    counts = {(group, component): count for group, component, count in rows}
    alerts = []
    for blood_group in sorted(BLOOD_GROUPS):
        for component in sorted(COMPONENTS):
            quantity = counts.get((blood_group, component), 0)
            if quantity <= threshold:
                alerts.append({
                    "blood_group": blood_group,
                    "component": component,
                    "available_units": quantity,
                    "threshold": threshold,
                    "level": "OUT_OF_STOCK" if quantity == 0 else "LOW_STOCK",
                })
    return alerts
