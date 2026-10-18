"""Database operations used by the web admin UI.

This was previously a single ``web/system.py`` module mixing item, purchase,
present, redeem and user operations. It is split into focused submodules here,
while re-exporting the same public functions so that existing
``web.system.<name>`` call sites keep working unchanged.
"""

from .items import get_all_item
from .presents import (
    add_one_present,
    delete_one_present,
    deliver_all_user_present,
    deliver_one_user_present,
    is_present_available,
)
from .purchases import get_all_purchase
from .redeems import add_one_redeem, add_some_random_redeem, delete_one_redeem
from .users import ban_one_user, change_userpwd, update_user_char

__all__ = [
    "get_all_item",
    "get_all_purchase",
    "add_one_present",
    "delete_one_present",
    "is_present_available",
    "deliver_one_user_present",
    "deliver_all_user_present",
    "add_one_redeem",
    "add_some_random_redeem",
    "delete_one_redeem",
    "update_user_char",
    "change_userpwd",
    "ban_one_user",
]
