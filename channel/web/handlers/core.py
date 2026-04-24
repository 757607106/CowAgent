from __future__ import annotations

import json
import os
import hmac
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import web


@dataclass(frozen=True)
class CoreHandlerDeps:
    is_password_enabled: Callable[[], bool]
    check_auth: Callable[[], bool]
    create_auth_token: Callable[[], str]
    session_expire_seconds: Callable[[], int]
    require_auth: Callable[[], None]
    get_expected_password: Callable[[], str]
    get_upload_dir: Callable[[], str]
    get_web_channel: Callable[[], Any]
    render_chat_page: Callable[[], str]
    resolve_asset_path: Callable[[str], Path | None]
    guess_content_type: Callable[[Path], str]
    logger: Any


def build_core_handlers(deps: CoreHandlerDeps) -> dict[str, type]:
    class RootHandler:
        def GET(self):
            raise web.seeother("/chat")

    class AuthCheckHandler:
        def GET(self):
            web.header("Content-Type", "application/json; charset=utf-8")
            if not deps.is_password_enabled():
                return json.dumps({"status": "success", "auth_required": False})
            if deps.check_auth():
                return json.dumps({"status": "success", "auth_required": True, "authenticated": True})
            return json.dumps({"status": "success", "auth_required": True, "authenticated": False})

    class AuthLoginHandler:
        def POST(self):
            web.header("Content-Type", "application/json; charset=utf-8")
            if not deps.is_password_enabled():
                return json.dumps({"status": "success"})
            try:
                data = json.loads(web.data())
            except Exception:
                return json.dumps({"status": "error", "message": "Invalid request"})

            password = data.get("password", "")
            expected = deps.get_expected_password()
            if not hmac.compare_digest(password, expected):
                deps.logger.warning("[WebChannel] Invalid login attempt")
                return json.dumps({"status": "error", "message": "Wrong password"})

            token = deps.create_auth_token()
            web.setcookie(
                "cow_auth_token",
                token,
                expires=deps.session_expire_seconds(),
                path="/",
                httponly=True,
                samesite="Lax",
            )
            return json.dumps({"status": "success"})

    class AuthLogoutHandler:
        def POST(self):
            web.header("Content-Type", "application/json; charset=utf-8")
            web.setcookie("cow_auth_token", "", expires=-1, path="/")
            return json.dumps({"status": "success"})

    class MessageHandler:
        def POST(self):
            deps.require_auth()
            web.header("Content-Type", "application/json; charset=utf-8")
            return deps.get_web_channel().post_message()

    class UploadHandler:
        def POST(self):
            deps.require_auth()
            web.header("Content-Type", "application/json; charset=utf-8")
            return deps.get_web_channel().upload_file()

    class UploadsHandler:
        def GET(self, file_name):
            deps.require_auth()
            try:
                upload_dir = deps.get_upload_dir()
                full_path = os.path.normpath(os.path.join(upload_dir, file_name))
                if not os.path.abspath(full_path).startswith(os.path.abspath(upload_dir)):
                    raise web.notfound()
                if not os.path.isfile(full_path):
                    raise web.notfound()
                content_type = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
                web.header("Content-Type", content_type)
                web.header("Cache-Control", "public, max-age=86400")
                with open(full_path, "rb") as f:
                    return f.read()
            except web.HTTPError:
                raise
            except Exception as e:
                deps.logger.error(f"[WebChannel] Error serving upload: {e}")
                raise web.notfound()

    class FileServeHandler:
        def GET(self):
            deps.require_auth()
            try:
                params = web.input(path="")
                file_path = params.path
                if not file_path or not os.path.isabs(file_path):
                    raise web.notfound()
                file_path = os.path.normpath(file_path)
                if not os.path.isfile(file_path):
                    raise web.notfound()
                content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                file_name = os.path.basename(file_path)
                from urllib.parse import quote

                web.header("Content-Type", content_type)
                web.header("Content-Disposition", f"inline; filename*=UTF-8''{quote(file_name)}")
                web.header("Cache-Control", "public, max-age=3600")
                with open(file_path, "rb") as f:
                    return f.read()
            except web.HTTPError:
                raise
            except Exception as e:
                deps.logger.error(f"[WebChannel] Error serving file: {e}")
                raise web.notfound()

    class PollHandler:
        def POST(self):
            deps.require_auth()
            return deps.get_web_channel().poll_response()

    class StreamHandler:
        def GET(self):
            deps.require_auth()
            params = web.input(request_id="")
            request_id = params.request_id
            if not request_id:
                raise web.badrequest()

            web.header("Content-Type", "text/event-stream; charset=utf-8")
            web.header("Cache-Control", "no-cache")
            web.header("X-Accel-Buffering", "no")
            web.header("Access-Control-Allow-Origin", "*")
            return deps.get_web_channel().stream_response(request_id)

    class ChatHandler:
        def GET(self):
            web.header("Cache-Control", "no-cache, no-store, must-revalidate")
            web.header("Pragma", "no-cache")
            return deps.render_chat_page()

    class AssetsHandler:
        def GET(self, file_path):
            try:
                full_path = deps.resolve_asset_path(file_path)
                if full_path is None:
                    deps.logger.error(f"File not found under frontend roots: {file_path}")
                    raise web.notfound()

                web.header("Content-Type", deps.guess_content_type(full_path))
                with open(full_path, "rb") as f:
                    return f.read()
            except web.HTTPError:
                raise
            except Exception as e:
                deps.logger.error(f"Error serving static file: {e}", exc_info=True)
                raise web.notfound()

    class VersionHandler:
        def GET(self):
            web.header("Content-Type", "application/json; charset=utf-8")
            from cli import __version__

            return json.dumps({"version": __version__})

    return {
        "RootHandler": RootHandler,
        "AuthCheckHandler": AuthCheckHandler,
        "AuthLoginHandler": AuthLoginHandler,
        "AuthLogoutHandler": AuthLogoutHandler,
        "MessageHandler": MessageHandler,
        "UploadHandler": UploadHandler,
        "UploadsHandler": UploadsHandler,
        "FileServeHandler": FileServeHandler,
        "PollHandler": PollHandler,
        "StreamHandler": StreamHandler,
        "ChatHandler": ChatHandler,
        "AssetsHandler": AssetsHandler,
        "VersionHandler": VersionHandler,
    }
