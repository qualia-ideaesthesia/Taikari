"""Example user configuration.

Copy this file to ``config.py`` in the same directory and adjust the values.
``config.py`` is listed in ``.gitignore`` and will not be committed, so it is a
safe place for credentials.

Only the attributes you actually define are applied; everything else keeps its
default value from ``core/config_manager.py``.

Alternatively you can point the server at a config file outside this folder with
the ``ARCAEA_SERVER_CONFIG`` environment variable, or use a JSON file through
``ARCAEA_JSON_CONFIG_PATH``.
"""


class Config:
    # Web admin panel credentials.
    USERNAME = "admin"
    PASSWORD = "change-me"

    # Flask session signing key. Use a long random string.
    SECRET_KEY = "change-me-to-a-random-secret"

    # Global API token. Leave empty to disable token-based API access.
    API_TOKEN = ""

    # Link Play shared secrets.
    # They are picked up by `linkplay_server` automatically, so you only need to
    # set them here.
    LINKPLAY_AUTHENTICATION = "change-me-linkplay-authentication"
    LINKPLAY_TCP_SECRET_KEY = "change-me-linkplay-tcp-secret"

    # Password of the built-in `admin` game account. It is only used when the
    # database is initialized for the first time.
    DEFAULT_ADMIN_PASSWORD = "change-me-admin-password"
