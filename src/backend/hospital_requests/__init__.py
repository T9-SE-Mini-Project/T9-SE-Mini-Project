"""Public entry point of the hospital_requests module.

Wired up in `main.py` (auth, DB session and inventory come from the other modules):

    app.include_router(create_router(get_session, require_role, InventoryCrossMatch(session_factory), load_settings()))

`InventoryCrossMatch` is the inventory module's implementation of CrossMatchInterface.
"""
from .config import Settings, load_settings
from .cross_match import CrossMatchInterface
from .routes import create_router

__all__ = ["CrossMatchInterface", "Settings", "load_settings", "create_router"]
