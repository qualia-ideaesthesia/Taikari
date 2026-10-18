"""Session-based CSRF protection for the web administration UI.

The game API authenticates with bearer tokens, not cookies, so CSRF does not
apply there. Only requests under ``/web`` are protected; the browser-side form
injection lives in ``templates/base.html``.
"""

import secrets

from flask import abort, request, session

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
_TOKEN_KEY = "_csrf_token"
_FORM_FIELD = "_csrf_token"


def get_csrf_token() -> str:
    """Return the per-session CSRF token, creating it on first use."""
    token = session.get(_TOKEN_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[_TOKEN_KEY] = token
    return token


def csrf_protect() -> None:
    """``before_request`` hook: validate the CSRF token for admin POSTs."""
    if request.method in _SAFE_METHODS:
        return
    # Only guard the cookie-authenticated admin UI.
    if not request.path.startswith("/web"):
        return

    token = session.get(_TOKEN_KEY)
    sent = request.form.get(_FORM_FIELD) or request.headers.get("X-CSRF-Token")
    if not token or not sent or not secrets.compare_digest(token, sent):
        abort(400, description="CSRF token missing or invalid.")
