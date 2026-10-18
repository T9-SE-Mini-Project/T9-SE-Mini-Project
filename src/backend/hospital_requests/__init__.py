"""Public entry point of the hospital_requests module.

Example wiring in the app (auth module and DB session come from the other owners):

    from hospital_requests import create_router, load_settings
    app.include_router(create_router(get_session, require_role, load_settings()))
"""
from .config import Settings, load_settings
from .routes import create_router

__all__ = ["Settings", "load_settings", "create_router"]
