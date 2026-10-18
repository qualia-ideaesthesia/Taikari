class Config:
    """
    Link Play server configuration
    """

    """
    Server address, port, verification code, and encryption key
    """
    HOST = "0.0.0.0"
    UDP_PORT = 8001
    TCP_PORT = 8002
    AUTHENTICATION = "change-me-linkplay-authentication"
    TCP_SECRET_KEY = "change-me-linkplay-tcp-secret"
    """
    --------------------------------------------------
    """

    DEBUG = False

    # Maximum number of UDP packets processed concurrently.
    UDP_WORKERS = 16

    TCP_MAX_LENGTH = 0x0FFFFFFF

    TIME_LIMIT = 3600000  # milliseconds, kept for compatibility
    TIME_LIMIT_US = TIME_LIMIT * 1000

    COMMAND_INTERVAL = 1000000

    PLAYER_PRE_TIMEOUT = 3000000
    PLAYER_TIMEOUT = 15000000

    LINK_PLAY_UNLOCK_LENGTH = 1024

    COUNTDOWN_SONG_READY = 5 * 1000000
    COUNTDOWN_SONG_START = 7 * 1000000

    # timed mode
    COUNTDOWN_MATCHING = 15 * 1000000
    COUNTDOWN_SELECT_SONG = 45 * 1000000
    COUNTDOWN_SELECT_DIFFICULTY = 45 * 1000000
    COUNTDOWN_RESULT = 60 * 1000000


# Keep the Link Play shared secrets in sync with the game server's optional
# `config.py`, so a single config file is enough. When no user config exists the
# placeholder values above are used (which are also the game server defaults).
try:
    from config import Config as _MainConfig  # type: ignore
except Exception:
    _MainConfig = None

if _MainConfig is not None:
    Config.AUTHENTICATION = getattr(
        _MainConfig, "LINKPLAY_AUTHENTICATION", Config.AUTHENTICATION
    )
    Config.TCP_SECRET_KEY = getattr(
        _MainConfig, "LINKPLAY_TCP_SECRET_KEY", Config.TCP_SECRET_KEY
    )
