"""Public entry point of the hospital_requests module.

Example wiring in the app (auth, DB session and inventory come from the other owners):

    from hospital_requests import create_router, load_settings
    app.include_router(create_router(get_session, require_role, inventory_service, load_settings()))

`inventory_service` is the inventory module's implementation of CrossMatchInterface.
"""
from .config import Settings, load_settings
from .cross_match import CrossMatchInterface
from .routes import create_router

__all__ = ["CrossMatchInterface", "Settings", "load_settings", "create_router"]
