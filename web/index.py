"""Web administration route registration."""

from web.blueprint import bp

from web import (
    catalog,
    characters,
    dashboard,
    database,
    gifts,
    moderation,
    users,
)  # noqa: F401,E402

__all__ = ["bp"]
