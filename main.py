import json
import os
import sys
from importlib import import_module
from importlib import util as importlib_util
from logging.config import dictConfig
from multiprocessing import Process, active_children, current_process, set_start_method
from traceback import format_exc

from core.config_manager import Config, ConfigManager


def _is_path(value: str) -> bool:
    if value.endswith(".py"):
        return True
    if os.path.isabs(value):
        return True
    if os.path.sep in value:
        return True
    if os.path.altsep and os.path.altsep in value:
        return True
    return False


def _load_config_from_path(config_path: str):
    config_path = os.path.abspath(config_path)
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config path not found: {config_path}")
    spec = importlib_util.spec_from_file_location("user_config", config_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import config from path: {config_path}")
    module = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "Config"):
        raise AttributeError(f"Config class not found in: {config_path}")
    return module.Config


def _load_user_config():
    config_target = os.getenv("ARCAEA_SERVER_CONFIG")
    if config_target:
        if _is_path(config_target):
            return _load_config_from_path(config_target)
        return import_module(config_target).Config
    if os.path.exists("config.py") or os.path.exists("config"):
        return import_module("config").Config
    return None


config_class = _load_user_config()
if config_class:

    ConfigManager.load(config_class)
else:

    configPath = os.environ.get("ARCAEA_JSON_CONFIG_PATH")
    if configPath and os.path.exists(configPath):
        with open(configPath, "r") as file:
            ConfigManager.load_dict(json.load(file))

if Config.DEPLOY_MODE == "gevent":

    from gevent import monkey  # type: ignore

    monkey.patch_all()


def _import_after_config():
    global Flask, request
    global api, server, web
    global BundleDownload, UserDownload, ArcError, InputError, NoAccess, RateLimit
    global FileChecker, Connect, error_return, DownloadManager

    from flask import Flask, request

    import api
    import server
    import web
    import web.index
    import web.login
    from core.bundle import BundleDownload
    from core.download import DownloadManager, UserDownload
    from core.error import ArcError, InputError, NoAccess, RateLimit
    from core.init import FileChecker
    from core.sql import Connect
    from server.func import error_return


_import_after_config()

app = Flask(__name__)

if Config.USE_PROXY_FIX:

    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
if Config.USE_CORS:

    from flask_cors import CORS  # type: ignore

    CORS(app, supports_credentials=True)

os.chdir(sys.path[0])

app.config.from_mapping(SECRET_KEY=Config.SECRET_KEY)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True

from web import security as web_security  # noqa: E402

app.before_request(web_security.csrf_protect)
app.jinja_env.globals["csrf_token"] = web_security.get_csrf_token

app.register_blueprint(web.login.bp)
app.register_blueprint(web.index.bp)
app.register_blueprint(api.bp)
list(map(app.register_blueprint, server.get_bps()))


def print_message_and_exit(message: str = ""):
    if message:
        print(message)
    children = active_children()
    if children:
        for child in children:
            try:
                child.terminate()
            except Exception:
                pass
        for child in children:
            try:
                child.join(timeout=2)
            except Exception:
                pass
    input("Press ENTER key to exit.")
    sys.exit(1)


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/favicon.ico", methods=["GET"])
def favicon():

    return app.send_static_file("favicon.ico")


@app.route("/download/<path:file_path>", methods=["GET"])
def download(file_path):
    with Connect(in_memory=True) as c:
        try:
            x = UserDownload(c)
            x.token = request.args.get("t")
            file_path_parts = file_path.split("/", 1)
            if len(file_path_parts) != 2:
                raise InputError("Invalid download path.")
            x.song_id, x.file_name = file_path_parts
            x.select_for_check()
            if x.is_limited:
                raise RateLimit(
                    f"User `{x.user.user_id}` has reached the download limit.", 903
                )
            if not x.is_valid:
                raise NoAccess("Expired token.")
            x.download_hit()
            return DownloadManager(file_path).get_response()
        except ArcError as e:
            if Config.ALLOW_WARNING_LOG:
                app.logger.warning(format_exc())
            return error_return(e)
    return error_return()


@app.route("/bundle_download/<string:token>", methods=["GET"])
def bundle_download(token: str):
    with Connect(in_memory=True) as c_m:
        try:
            file_path = BundleDownload(c_m).get_path_by_token(
                token, request.remote_addr
            )
            return DownloadManager(file_path, is_bundle=True).get_response()
        except ArcError as e:
            if Config.ALLOW_WARNING_LOG:
                app.logger.warning(format_exc())
            return error_return(e)
    return error_return()


if Config.DEPLOY_MODE == "waitress":

    @app.after_request
    def after_request(response):
        app.logger.info(
            f"{request.remote_addr} - - {request.method} {request.path} {response.status_code}"
        )
        return response


def tcp_server_run():
    if Config.DEPLOY_MODE == "gevent":

        host_port = (Config.HOST, Config.PORT)
        app.logger.info("Running gevent WSGI server... (%s:%s)" % host_port)
        from gevent.pywsgi import WSGIServer  # type: ignore

        WSGIServer(host_port, app, log=app.logger).serve_forever()
    elif Config.DEPLOY_MODE == "waitress":

        import logging

        from waitress import serve  # type: ignore

        logger = logging.getLogger("waitress")
        logger.setLevel(logging.INFO)
        serve(
            app,
            host=Config.HOST,
            port=Config.PORT,
            clear_untrusted_proxy_headers=not Config.USE_PROXY_FIX,
        )
    elif Config.DEPLOY_MODE == "gunicorn":

        if os.name == "nt":
            app.logger.error(
                "Gunicorn is not supported on Windows. Use waitress instead."
            )
            print_message_and_exit()
        try:
            from gunicorn.app.base import BaseApplication  # type: ignore
        except Exception:
            app.logger.error(
                "Gunicorn is not installed. Install it with `pip install gunicorn`."
            )
            print_message_and_exit()

        class GunicornApplication(BaseApplication):
            def __init__(self, application, options=None):
                self.options = options or {}
                self.application = application
                super().__init__()

            def load_config(self):
                for key, value in self.options.items():
                    if value is None:
                        continue
                    self.cfg.set(key, value)

            def load(self):
                return self.application

        GunicornApplication(app, Config.DEPLOY_OPTIONS["gunicorn"]).run()
    else:
        if Config.SSL_CERT and Config.SSL_KEY:
            app.run(
                Config.HOST, Config.PORT, ssl_context=(Config.SSL_CERT, Config.SSL_KEY)
            )
        else:
            app.run(Config.HOST, Config.PORT)


def generate_log_file_dict(level: str, filename: str) -> dict:
    return {
        "class": "logging.handlers.RotatingFileHandler",
        "maxBytes": 1024 * 1024,
        "backupCount": 1,
        "encoding": "utf-8",
        "level": level,
        "formatter": "default",
        "filename": filename,
    }


_INSECURE_DEFAULT_VALUES = {
    "SECRET_KEY": "change-me-to-a-random-secret",
    "USERNAME": "admin",
    "PASSWORD": "change-me",
    "LINKPLAY_AUTHENTICATION": "change-me-linkplay-authentication",
    "LINKPLAY_TCP_SECRET_KEY": "change-me-linkplay-tcp-secret",
}


def warn_insecure_defaults(logger) -> None:
    """Warn loudly when authentication-critical settings keep default values."""
    defaults = [
        name
        for name, value in _INSECURE_DEFAULT_VALUES.items()
        if getattr(Config, name, None) == value
    ]
    if defaults:
        logger.warning(
            "The following settings still use their insecure default values: "
            "%s. Change them before exposing this server to a network.",
            ", ".join(defaults),
        )


def pre_main():
    log_dict = {
        "version": 1,
        "root": {"level": "INFO", "handlers": ["wsgi", "error_file"]},
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            },
            "error_file": generate_log_file_dict(
                "ERROR", f"{Config.LOG_FOLDER_PATH}/error.log"
            ),
        },
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
            }
        },
    }
    if Config.ALLOW_INFO_LOG:
        log_dict["root"]["handlers"].append("info_file")
        log_dict["handlers"]["info_file"] = generate_log_file_dict(
            "INFO", f"{Config.LOG_FOLDER_PATH}/info.log"
        )
    if Config.ALLOW_WARNING_LOG:
        log_dict["root"]["handlers"].append("warning_file")
        log_dict["handlers"]["warning_file"] = generate_log_file_dict(
            "WARNING", f"{Config.LOG_FOLDER_PATH}/warning.log"
        )

    dictConfig(log_dict)

    Connect.logger = app.logger
    warn_insecure_defaults(app.logger)
    if not FileChecker(app.logger).check_before_run():
        app.logger.error("Some errors occurred. The server will not run.")
        print_message_and_exit()


def main():
    processes = []
    if Config.LINKPLAY_HOST and Config.SET_LINKPLAY_SERVER_AS_SUB_PROCESS:
        from linkplay_server import link_play

        processes = [
            Process(
                target=link_play,
                args=(
                    Config.LINKPLAY_HOST,
                    int(Config.LINKPLAY_UDP_PORT),
                    int(Config.LINKPLAY_TCP_PORT),
                ),
            )
        ]
        [p.start() for p in processes]
        app.logger.info(
            f"Link Play UDP server is running on {Config.LINKPLAY_HOST}:{Config.LINKPLAY_UDP_PORT} ..."
        )
        app.logger.info(
            f"Link Play TCP server is running on {Config.LINKPLAY_HOST}:{Config.LINKPLAY_TCP_PORT} ..."
        )

    try:
        tcp_server_run()
    finally:
        for p in processes:
            if p.is_alive():
                p.terminate()
        for p in processes:
            p.join(timeout=5)
            if p.is_alive():
                p.kill()


if current_process().name == "MainProcess":
    pre_main()

if __name__ == "__main__":
    set_start_method("spawn")
    try:
        main()
    except KeyboardInterrupt:
        pass
