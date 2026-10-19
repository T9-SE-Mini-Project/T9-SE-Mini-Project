"""Settings for the hospital_requests module, read from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    max_units_per_request: int = 10


def load_settings() -> Settings:
    """Build Settings from the environment (no hard-coded values)."""
    return Settings(
        max_units_per_request=int(os.environ.get("MAX_UNITS_PER_REQUEST", "10")),
    )
