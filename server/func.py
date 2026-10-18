from functools import wraps
from traceback import format_exc

from flask import current_app, g, jsonify

from core.bundle import BundleParser
from core.config_manager import Config
from core.error import ArcError, LowVersion, NoAccess

has_arc_hash = False
try:
    from core.arc_crypto import ArcHashChecker  # type: ignore
    has_arc_hash = True
except ModuleNotFoundError:
    pass

default_error = ArcError('Unknown Error', status=500)


def error_return(e: ArcError = default_error):  # Error return
    # -7 An error occurred while processing the transaction
    # -5 All songs have already been downloaded
    # -4 Your account is logged in elsewhere
    # -3 Unable to connect to the server
    # 2 The Arcaea server is under maintenance
    # 5 Please update Arcaea to the latest version
    # 9 Please wait a few minutes for the new version
    # 11 Game content needs updating, returning to the main screen
    # 100 Unable to log into the game from this IP address
    # 101 Username taken
    # 102 Email already registered
    # 103 An account has already been created from this device
    # 104 Incorrect username or password
    # 105 Logged into two devices within 24 hours
    # 106 121 Account frozen
    # 107 You do not have enough stamina
    # 113 The event has ended
    # 114 The event has ended, your score will not be submitted
    # 115 Please enter a valid email address
    # 120 Ban warning
    # 122 Account temporarily frozen
    # 123 Account restricted
    # 124 You cannot create new accounts from this IP address again today
    # 150 Sorry, you have been restricted from using this feature
    # 151 This feature is currently unavailable
    # 160 Account not email-verified, please check your email
    # 161 Account verification expired, please register again
    # 401 User does not exist
    # 403 Unable to connect to the server
    # 501 502 -6 This item is currently unavailable
    # 504 Invalid serial code
    # 505 This serial code has already been used
    # 506 You already own this item
    # 601 Friend list is full
    # 602 This user is already a friend
    # 604 You cannot add yourself as a friend
    # 903 Download limit exceeded, please retry after 24 hours
    # 905 Please wait 24 hours before using this feature again
    # 910 Wait x minutes before requesting the verification email again extra: retry_at
    # 1001 Device count limit reached
    # 1002 This device has already used this feature
    # 1201 Room is full
    # 1202 Invalid room code
    # 1203 Please update Arcaea to the latest version
    # 1205 Unable to join this room at the moment
    # 9801 A problem occurred while downloading the song, please try again
    # 9802 A problem occurred while saving the song, please check your device storage
    # 9803 Download cancelled
    # 9905 No data found in the cloud
    # 9907 A problem occurred while updating data
    # 9908 The server only supports the latest version, please update Arcaea
    # Others An unknown error occurred
    r = {"success": False, "error_code": e.error_code}
    if e.extra_data:
        r['extra'] = e.extra_data

    return jsonify(r), e.status


def success_return(value=None):
    r = {"success": True}
    if value is not None:
        r['value'] = value
    return jsonify(r)


def arc_try(view):
    '''Alternative to try/except, logs `ArcError` as a warning'''
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        try:
            data = view(*args, **kwargs)
            if data is None:
                return error_return()
            return data
        except ArcError as e:
            if Config.ALLOW_WARNING_LOG:
                current_app.logger.warning(format_exc())
            user = g.get("user", None)
            current_app.logger.warning(
                f'{user.user_id if user is not None else ""} - {e.error_code}|{e.api_error_code}: {e}')
            return error_return(e)
        except Exception:
            # Unexpected errors are logged with a full traceback and reported as
            # a generic server error instead of leaking internals or 500-ing.
            current_app.logger.error(format_exc())
            return error_return(default_error)

    return wrapped_view


def header_check(request) -> ArcError:
    '''Check whether the request headers are valid'''
    headers = request.headers
    if Config.ALLOW_APPVERSION:  # Version check
        if 'AppVersion' not in headers or headers['AppVersion'] not in Config.ALLOW_APPVERSION:
            return LowVersion('Invalid app version', 5)
    if request.method == 'GET' and 'ContentBundle' in headers and headers['ContentBundle'] != BundleParser.max_bundle_version.get(headers.get('AppVersion', ''), '0.0.0'):
        return LowVersion('Invalid content bundle version', 11)

    if has_arc_hash and not ArcHashChecker(request).check():
        return NoAccess('Invalid request')

    return None
