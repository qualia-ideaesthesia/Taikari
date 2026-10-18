import base64
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request

from core.error import ArcError, NoAccess, PostError
from core.sql import Connect
from core.user import UserAuth, UserLogin

from .func import arc_try, error_return, header_check

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['POST'])  # Login endpoint
@arc_try
def login():
    headers = request.headers
    e = header_check(request)
    if e is not None:
        raise e

    if not request.form.get('grant_type'):
        raise PostError('Missing grant_type')
    auth_header = headers.get('Authorization')
    if not auth_header:
        raise PostError('Missing Authorization header')
    try:
        id_pwd = base64.b64decode(auth_header[6:]).decode()
    except Exception:
        raise PostError('Invalid Authorization header')
    if ':' not in id_pwd:
        raise PostError('Invalid Authorization header')
    name, password = id_pwd.split(':', 1)
    with Connect() as c:
        if 'DeviceId' in headers:
            device_id = headers['DeviceId']
        else:
            device_id = 'low_version'

        user = UserLogin(c)
        user.login(name, password, device_id, request.remote_addr)
        current_app.logger.info(f'User `{user.user_id}` log in')
        return jsonify({"success": True, "token_type": "Bearer", 'user_id': user.user_id, 'access_token': user.token})


def auth_required(req):
    # Arcaea login verification, written as a decorator
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):

            headers = req.headers

            e = header_check(req)
            if e is not None:
                current_app.logger.warning(
                    f' - {e.error_code}|{e.api_error_code}: {e}')
                return error_return(e)

            with Connect() as c:
                try:
                    user = UserAuth(c)
                    token = headers.get('Authorization')
                    if not token:
                        raise NoAccess('No token.', -4)
                    user.token = token[7:]
                    user_id = user.token_get_id()
                    g.user = user
                except ArcError as e:
                    return error_return(e)
            return view(user_id, *args, **kwargs)

        return wrapped_view
    return decorator
