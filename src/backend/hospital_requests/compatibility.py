"""Blood group compatibility rules (BLOOD-16).

The rules now live in the shared `blood` module so inventory and hospital_requests use
one copy. This module re-exports them so existing imports keep working.
"""
from __future__ import annotations

from ..blood import compatible_donor_groups, is_compatible

__all__ = ["compatible_donor_groups", "is_compatible"]
