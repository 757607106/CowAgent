import hashlib
import hmac
import time
import json
import logging
import os
import threading
import uuid
from pathlib import Path
from queue import Queue, Empty

import web

from bridge.context import *
from bridge.reply import Reply, ReplyType
from channel.chat_channel import ChatChannel, check_prefix
from channel.chat_message import ChatMessage
from common.log import logger
from common.singleton import singleton
from config import conf
from cow_platform.runtime.tenant_scope import (
    TenantScopeError,
    normalize_tenant_id,
    resolve_tenant_scope,
)
from channel.web.frontend_layout import (
    FRONTEND_MODE_MODERN,
    build_frontend_layout,
    guess_content_type,
    render_chat_html,
    resolve_asset_file,
)
from channel.web.handlers import CoreHandlerDeps, build_core_handlers
from channel.web.route_table import build_web_routes

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".avi", ".mov", ".mkv"}
_FRONTEND_LAYOUT = build_frontend_layout(__file__)
_FRONTEND_MODE_WARNED = False
_AUTH_COOKIE = "cow_auth_token"
_TENANT_AUTH_COOKIE = "cow_tenant_auth_token"


def _frontend_mode() -> str:
    global _FRONTEND_MODE_WARNED
    requested = str(conf().get("web_frontend_mode", FRONTEND_MODE_MODERN) or FRONTEND_MODE_MODERN).strip().lower()
    if requested and requested != FRONTEND_MODE_MODERN and not _FRONTEND_MODE_WARNED:
        logger.warning(
            "[WebChannel] web_frontend_mode=%s is deprecated; modern frontend is always enabled now.",
            requested,
        )
        _FRONTEND_MODE_WARNED = True
    return FRONTEND_MODE_MODERN

def _is_password_enabled():
    return bool(conf().get("web_password", ""))


def _is_tenant_auth_enabled():
    return bool(conf().get("web_tenant_auth", True))


def _session_expire_seconds():
    return int(conf().get("web_session_expire_days", 30)) * 86400


def _create_auth_token():
    """Create a stateless signed token: ``<timestamp_hex>.<hmac_hex>``."""
    ts = format(int(time.time()), "x")
    sig = hmac.new(
        conf().get("web_password", "").encode(),
        ts.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{ts}.{sig}"


def _verify_auth_token(token):
    """Verify a signed token is valid and not expired.

    The token is derived from the password, so it survives server restarts
    and automatically invalidates when the password changes.
    """
    if not token or "." not in token:
        return False
    ts_hex, sig = token.split(".", 1)
    try:
        ts = int(ts_hex, 16)
    except ValueError:
        return False
    if time.time() - ts > _session_expire_seconds():
        return False
    expected = hmac.new(
        conf().get("web_password", "").encode(),
        ts_hex.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(sig, expected)


def _get_auth_service():
    from cow_platform.services.auth_service import TenantAuthService

    return TenantAuthService(session_expire_seconds=_session_expire_seconds())


def _get_cookie_value(name: str) -> str:
    try:
        cookies = web.cookies()
        return cookies.get(name, "")
    except Exception:
        return ""


def _get_authenticated_tenant_session():
    if not _is_tenant_auth_enabled():
        return None
    return _get_auth_service().verify_session_token(_get_cookie_value(_TENANT_AUTH_COOKIE))


def _is_platform_admin_session(session=None) -> bool:
    session = session or _get_authenticated_tenant_session()
    return bool(session and session.principal_type == "platform" and session.role == "platform_super_admin")


def _check_auth():
    """Return True if request is authenticated or password not enabled."""
    if _is_tenant_auth_enabled():
        return _get_authenticated_tenant_session() is not None
    if not _is_password_enabled():
        return True
    return _verify_auth_token(_get_cookie_value(_AUTH_COOKIE))


def _check_auth_payload() -> dict[str, object]:
    if _is_tenant_auth_enabled():
        service = _get_auth_service()
        session = service.verify_session_token(_get_cookie_value(_TENANT_AUTH_COOKIE))
        return {
            "status": "success",
            "auth_required": True,
            "auth_mode": "tenant",
            "authenticated": session is not None,
            "bootstrap_required": not service.has_credentials(),
            "platform_bootstrap_required": not service.has_platform_admin(),
            "user": session.to_public_dict() if session else None,
        }
    if not _is_password_enabled():
        return {"status": "success", "auth_required": False, "auth_mode": "none"}
    return {
        "status": "success",
        "auth_required": True,
        "auth_mode": "password",
        "authenticated": _verify_auth_token(_get_cookie_value(_AUTH_COOKIE)),
    }


def _set_auth_cookie(name: str, value: str):
    web.setcookie(
        name,
        value,
        expires=_session_expire_seconds(),
        path="/",
        httponly=True,
        samesite="Lax",
    )


def _login(data: dict[str, object]) -> dict[str, object]:
    if _is_tenant_auth_enabled():
        service = _get_auth_service()
        try:
            if data.get("account"):
                session = service.authenticate_account(
                    account=str(data.get("account", "") or ""),
                    password=str(data.get("password", "") or ""),
                )
            else:
                session = service.authenticate(
                    tenant_id=str(data.get("tenant_id", "") or ""),
                    user_id=str(data.get("user_id", "") or ""),
                    password=str(data.get("password", "") or ""),
                )
        except Exception:
            logger.warning("[WebChannel] Invalid tenant login attempt")
            return {"status": "error", "message": "账号或密码不正确"}
        _set_auth_cookie(_TENANT_AUTH_COOKIE, service.create_session_token(session))
        web.setcookie(_AUTH_COOKIE, "", expires=-1, path="/")
        return {"status": "success", "user": session.to_public_dict()}

    if not _is_password_enabled():
        return {"status": "success"}

    password = str(data.get("password", "") or "")
    expected = conf().get("web_password", "")
    if not hmac.compare_digest(password, expected):
        logger.warning("[WebChannel] Invalid login attempt")
        return {"status": "error", "message": "Wrong password"}

    _set_auth_cookie(_AUTH_COOKIE, _create_auth_token())
    web.setcookie(_TENANT_AUTH_COOKIE, "", expires=-1, path="/")
    return {"status": "success"}


def _register(data: dict[str, object]) -> dict[str, object]:
    if not _is_tenant_auth_enabled():
        return {"status": "error", "message": "tenant auth is disabled"}

    try:
        service = _get_auth_service()
        result = service.register_tenant(
            tenant_id=str(data.get("tenant_id", "") or ""),
            tenant_name=str(data.get("tenant_name", "") or data.get("name", "") or ""),
            user_id=str(data.get("user_id", "") or ""),
            account=str(data.get("account", "") or ""),
            name=str(data.get("user_name", "") or data.get("name", "") or ""),
            password=str(data.get("password", "") or ""),
        )
        if data.get("account"):
            session = service.authenticate_account(
                account=str(data.get("account", "") or ""),
                password=str(data.get("password", "") or ""),
            )
        else:
            session = service.authenticate(
                tenant_id=result["tenant"]["tenant_id"],
                user_id=result["tenant_user"]["user_id"],
                password=str(data.get("password", "") or ""),
            )
        _set_auth_cookie(_TENANT_AUTH_COOKIE, service.create_session_token(session))
        web.setcookie(_AUTH_COOKIE, "", expires=-1, path="/")
        return {"status": "success", **result, "user": session.to_public_dict()}
    except Exception as e:
        logger.warning(f"[WebChannel] Tenant register failed: {e}")
        return {"status": "error", "message": str(e)}


def _register_platform_admin(data: dict[str, object]) -> dict[str, object]:
    if not _is_tenant_auth_enabled():
        return {"status": "error", "message": "tenant auth is disabled"}

    try:
        service = _get_auth_service()
        result = service.register_platform_admin(
            account=str(data.get("account", "") or ""),
            name=str(data.get("name", "") or data.get("user_name", "") or ""),
            password=str(data.get("password", "") or ""),
        )
        session = service.authenticate_account(
            account=str(data.get("account", "") or ""),
            password=str(data.get("password", "") or ""),
        )
        _set_auth_cookie(_TENANT_AUTH_COOKIE, service.create_session_token(session))
        web.setcookie(_AUTH_COOKIE, "", expires=-1, path="/")
        return {"status": "success", **result, "user": session.to_public_dict()}
    except Exception as e:
        logger.warning(f"[WebChannel] Platform admin register failed: {e}")
        return {"status": "error", "message": str(e)}


def _logout() -> None:
    web.setcookie(_AUTH_COOKIE, "", expires=-1, path="/")
    web.setcookie(_TENANT_AUTH_COOKIE, "", expires=-1, path="/")


def _require_auth():
    """Raise 401 if not authenticated. Call at the top of protected handlers."""
    if not _check_auth():
        raise web.HTTPError("401 Unauthorized",
                            {"Content-Type": "application/json; charset=utf-8"},
                            json.dumps({"status": "error", "message": "Unauthorized"}))


def _require_platform_admin():
    _require_auth()
    if _is_tenant_auth_enabled() and not _is_platform_admin_session():
        _raise_forbidden("需要平台超级管理员权限")


def _require_tenant_manage():
    _require_auth()
    session = _get_authenticated_tenant_session()
    if session and session.principal_type != "tenant":
        _raise_forbidden("需要租户用户权限")
    if session and session.role not in {"owner", "admin"}:
        _raise_forbidden("需要租户管理员权限")


def _raise_forbidden(message: str = "Forbidden"):
    raise web.HTTPError(
        "403 Forbidden",
        {"Content-Type": "application/json; charset=utf-8"},
        json.dumps({"status": "error", "message": message}, ensure_ascii=False),
    )


def _get_upload_dir(agent_id: str = "", tenant_id: str = "", binding_id: str = "") -> str:
    ws_root = _get_workspace_root(agent_id=agent_id, tenant_id=tenant_id, binding_id=binding_id)
    tmp_dir = os.path.join(ws_root, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    return tmp_dir


def _normalize_tenant_id(tenant_id: str = "") -> str:
    return normalize_tenant_id(tenant_id)


def _normalize_agent_id(agent_id: str = "") -> str:
    return (agent_id or "default").strip() or "default"


def _normalize_binding_id(binding_id: str = "") -> str:
    return (binding_id or "").strip()


def _scope_tenant_id(tenant_id: str = "", *, default: str = "default") -> str:
    """Resolve a tenant id under the current authenticated tenant session."""
    session = _get_authenticated_tenant_session()
    if session:
        if session.principal_type == "platform":
            _raise_forbidden("需要租户用户权限")
        try:
            return resolve_tenant_scope(
                session_tenant_id=session.tenant_id,
                requested_tenant_id=tenant_id,
                default_tenant_id=default,
            )
        except TenantScopeError:
            _raise_forbidden("不能访问其他租户的数据")
    return normalize_tenant_id(tenant_id or default, default=default)


def _scope_optional_tenant_id(tenant_id: str = "") -> str:
    """Like _scope_tenant_id, but preserves blank tenant filters in legacy mode."""
    session = _get_authenticated_tenant_session()
    if session:
        if session.principal_type == "platform":
            _raise_forbidden("需要租户用户权限")
        try:
            return resolve_tenant_scope(
                session_tenant_id=session.tenant_id,
                requested_tenant_id=tenant_id,
                default_tenant_id="default",
                preserve_blank_without_session=True,
            )
        except TenantScopeError:
            _raise_forbidden("不能访问其他租户的数据")
    return resolve_tenant_scope(
        requested_tenant_id=tenant_id,
        default_tenant_id="default",
        preserve_blank_without_session=True,
    )


def _parse_bool(value, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("0", "false", "off", "no", "disabled"):
            return False
        if text in ("1", "true", "on", "yes", "enabled"):
            return True
    return bool(value)


def _get_agent_service():
    from cow_platform.services.agent_service import AgentService

    return AgentService()


def _get_mcp_server_service():
    from cow_platform.services.mcp_server_service import TenantMcpServerService

    return TenantMcpServerService()


def _get_tenant_service():
    from cow_platform.services.tenant_service import TenantService

    return TenantService()


def _get_tenant_user_service():
    from cow_platform.services.tenant_user_service import TenantUserService

    return TenantUserService()


def _get_model_config_service():
    from cow_platform.services.model_config_service import ModelConfigService

    return ModelConfigService()


def _get_channel_config_service():
    from cow_platform.services.channel_config_service import ChannelConfigService

    return ChannelConfigService()


def _get_binding_service():
    from cow_platform.services.binding_service import ChannelBindingService

    return ChannelBindingService()


def _get_usage_service():
    from cow_platform.services.usage_service import UsageService

    return UsageService()


def _get_session_repository():
    from cow_platform.repositories.session_repository import SessionRepository

    return SessionRepository()


def _get_runtime_adapter():
    from cow_platform.adapters.cowagent_runtime_adapter import CowAgentRuntimeAdapter

    return CowAgentRuntimeAdapter()


def _restart_channel_config_runtime(channel_config_id: str):
    try:
        import sys

        app_module = sys.modules.get('__main__') or sys.modules.get('app')
        mgr = getattr(app_module, '_channel_mgr', None) if app_module else None
        if not mgr:
            return
        definition = _get_channel_config_service().resolve_channel_config(channel_config_id=channel_config_id)
        if definition.enabled:
            mgr.start_channel_config(definition)
        else:
            mgr.remove_channel_config(channel_config_id)
    except Exception as e:
        logger.warning(f"[WebChannel] channel config runtime refresh skipped: {e}")


def _stop_channel_config_runtime(channel_config_id: str):
    try:
        import sys

        app_module = sys.modules.get('__main__') or sys.modules.get('app')
        mgr = getattr(app_module, '_channel_mgr', None) if app_module else None
        if mgr:
            mgr.remove_channel_config(channel_config_id)
    except Exception as e:
        logger.warning(f"[WebChannel] channel config runtime stop skipped: {e}")


def _is_file_access_allowed(file_path: str) -> bool:
    session = _get_authenticated_tenant_session()
    if session is None:
        return True
    try:
        from cow_platform.repositories.agent_repository import get_platform_workspace_root
        from cow_platform.runtime.namespaces import normalize_namespace_segment

        allowed_root = (
            get_platform_workspace_root()
            / normalize_namespace_segment(session.tenant_id)
        ).resolve()
        target = Path(file_path).resolve()
        target.relative_to(allowed_root)
        return True
    except Exception:
        logger.warning(
            f"[WebChannel] Blocked cross-tenant file access: tenant={session.tenant_id}, path={file_path}"
        )
        return False


def _resolve_runtime_target(agent_id: str = "", tenant_id: str = "", binding_id: str = "") -> dict[str, str]:
    """把页面上传入的 agent_id / binding_id 解析成最终路由目标。"""
    raw_binding_id = _normalize_binding_id(binding_id)
    if raw_binding_id:
        binding = _get_binding_service().resolve_binding(
            binding_id=raw_binding_id,
            tenant_id=_scope_optional_tenant_id(tenant_id),
        )
        return {
            "tenant_id": binding.tenant_id,
            "agent_id": binding.agent_id,
            "binding_id": binding.binding_id,
        }

    raw_agent_id = (agent_id or "").strip()
    if raw_agent_id:
        return {
            "tenant_id": _scope_tenant_id(tenant_id),
            "agent_id": _normalize_agent_id(raw_agent_id),
            "binding_id": "",
        }

    session = _get_authenticated_tenant_session()
    if session:
        return {
            "tenant_id": session.tenant_id,
            "agent_id": "default",
            "binding_id": "",
        }

    return {
        "tenant_id": _normalize_tenant_id(tenant_id),
        "agent_id": "",
        "binding_id": "",
    }


def _get_session_store(agent_id: str = "", tenant_id: str = "", binding_id: str = ""):
    from agent.memory import get_conversation_store

    target = _resolve_runtime_target(agent_id=agent_id, tenant_id=tenant_id, binding_id=binding_id)
    if not target["agent_id"]:
        return get_conversation_store()
    workspace_root = _get_workspace_root(
        agent_id=target["agent_id"],
        tenant_id=target["tenant_id"],
        binding_id=target["binding_id"],
    )
    return get_conversation_store(workspace_root=workspace_root)


def _generate_session_title(user_message: str, assistant_reply: str = "") -> str:
    """
    Generate a short session title by calling the current bot's reply_text.
    """
    import re
    fallback = user_message[:50].split("\n")[0].strip() or "New Chat"
    try:
        from bridge.bridge import Bridge
        from models.session_manager import Session
        bot = Bridge().get_bot("chat")

        prompt_parts = [f"User: {user_message[:300]}"]
        if assistant_reply:
            prompt_parts.append(f"Assistant: {assistant_reply[:300]}")

        session = Session("__title_gen__", system_prompt="")
        session.messages = [
            {"role": "user", "content": (
                "Generate a very short title (max 15 characters for Chinese, max 6 words for English) "
                "summarizing this conversation. Return ONLY the title text, nothing else.\n\n"
                + "\n".join(prompt_parts)
            )}
        ]

        result = bot.reply_text(session)
        raw = (result.get("content") or "").strip()
        # Strip <think>...</think> reasoning blocks
        title = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip().strip('"\'')
        logger.info(f"[WebChannel] Title generation result: '{title}' (len={len(title)})")
        if title and len(title) <= 50:
            return title
    except Exception as e:
        logger.warning(f"[WebChannel] Title generation failed: {e}")
    return fallback


class WebMessage(ChatMessage):
    def __init__(
            self,
            msg_id,
            content,
            ctype=ContextType.TEXT,
            from_user_id="User",
            to_user_id="Chatgpt",
            other_user_id="Chatgpt",
    ):
        self.msg_id = msg_id
        self.ctype = ctype
        self.content = content
        self.from_user_id = from_user_id
        self.to_user_id = to_user_id
        self.other_user_id = other_user_id


@singleton
class WebChannel(ChatChannel):
    NOT_SUPPORT_REPLYTYPE = [ReplyType.VOICE]
    _instance = None

    # def __new__(cls):
    #     if cls._instance is None:
    #         cls._instance = super(WebChannel, cls).__new__(cls)
    #     return cls._instance

    def __init__(self):
        super().__init__()
        self.msg_id_counter = 0
        self.session_queues = {}  # scoped_session_key -> Queue (fallback polling)
        self.request_to_session = {}  # request_id -> scoped_session_key
        self.sse_queues = {}  # request_id -> Queue (SSE streaming)
        self.session_to_request = {}  # scoped_session_key -> latest request_id (for preemption)
        self._http_server = None

    def _generate_msg_id(self):
        """生成唯一的消息ID"""
        self.msg_id_counter += 1
        return str(int(time.time())) + str(self.msg_id_counter)

    def _generate_request_id(self):
        """生成唯一的请求ID"""
        return str(uuid.uuid4())

    def _build_scoped_session_key(self, session_id: str, agent_id: str = "default", tenant_id: str = "default") -> str:
        """构造 Web 通道内部使用的会话键。"""
        return f"{_normalize_tenant_id(tenant_id)}:{_normalize_agent_id(agent_id)}:{session_id}"

    def send(self, reply: Reply, context: Context):
        try:
            if reply.type in self.NOT_SUPPORT_REPLYTYPE:
                logger.warning(f"Web channel doesn't support {reply.type} yet")
                return

            if reply.type == ReplyType.IMAGE_URL:
                time.sleep(0.5)

            request_id = context.get("request_id", None)
            if not request_id:
                logger.error("No request_id found in context, cannot send message")
                return

            session_id = self.request_to_session.get(request_id)
            if not session_id:
                logger.error(f"No session_id found for request {request_id}")
                return

            # SSE mode: push events to SSE queue
            if request_id in self.sse_queues:
                content = reply.content if reply.content is not None else ""

                # Intermediate status lines (e.g. /install-browser phases) must NOT use "done",
                # or the frontend closes EventSource and drops subsequent events.
                if getattr(reply, "sse_phase", False):
                    self.sse_queues[request_id].put({
                        "type": "phase",
                        "content": content,
                        "request_id": request_id,
                        "timestamp": time.time(),
                    })
                    logger.debug(f"SSE phase for request {request_id}")
                    return

                # Files are already pushed via on_event (file_to_send) during agent execution.
                # Skip duplicate file pushes here; just let the done event through.
                if reply.type in (ReplyType.IMAGE_URL, ReplyType.FILE) and content.startswith("file://"):
                    text_content = getattr(reply, 'text_content', '')
                    if text_content:
                        self.sse_queues[request_id].put({
                            "type": "done",
                            "content": text_content,
                            "request_id": request_id,
                            "timestamp": time.time()
                        })
                    logger.debug(f"SSE skipped duplicate file for request {request_id}")
                    return

                # Skip http-URL FILE/IMAGE_URL replies produced by chat_channel's media extraction:
                # the text reply (already sent as "done") contains the URL and the frontend will
                # render it via renderMarkdown/injectVideoPlayers, so no separate SSE event needed.
                if reply.type in (ReplyType.FILE, ReplyType.IMAGE_URL) and content.startswith(("http://", "https://")):
                    logger.debug(f"SSE skipped http media reply for request {request_id}")
                    return

                self.sse_queues[request_id].put({
                    "type": "done",
                    "content": content,
                    "request_id": request_id,
                    "timestamp": time.time()
                })
                logger.debug(f"SSE done sent for request {request_id}")
                return

            # Fallback: polling mode
            if session_id in self.session_queues:
                response_data = {
                    "type": str(reply.type),
                    "content": reply.content,
                    "timestamp": time.time(),
                    "request_id": request_id
                }
                self.session_queues[session_id].put(response_data)
                logger.debug(f"Response sent to poll queue for session {session_id}, request {request_id}")
            else:
                logger.warning(f"No response queue found for session {session_id}, response dropped")

        except Exception as e:
            logger.error(f"Error in send method: {e}")

    def _make_sse_callback(self, request_id: str):
        """Build an on_event callback that pushes agent stream events into the SSE queue."""

        def on_event(event: dict):
            if request_id not in self.sse_queues:
                return
            q = self.sse_queues[request_id]
            event_type = event.get("type")
            data = event.get("data", {})

            if event_type == "reasoning_update":
                delta = data.get("delta", "")
                if delta:
                    q.put({"type": "reasoning", "content": delta})

            elif event_type == "message_update":
                delta = data.get("delta", "")
                if delta:
                    q.put({"type": "delta", "content": delta})

            elif event_type == "tool_execution_start":
                tool_name = data.get("tool_name", "tool")
                arguments = data.get("arguments", {})
                q.put({"type": "tool_start", "tool": tool_name, "arguments": arguments})

            elif event_type == "tool_execution_end":
                tool_name = data.get("tool_name", "tool")
                status = data.get("status", "success")
                result = data.get("result", "")
                exec_time = data.get("execution_time", 0)
                # Truncate long results to avoid huge SSE payloads
                result_str = str(result)
                if len(result_str) > 2000:
                    result_str = result_str[:2000] + "…"
                q.put({
                    "type": "tool_end",
                    "tool": tool_name,
                    "status": status,
                    "result": result_str,
                    "execution_time": round(exec_time, 2)
                })

            elif event_type == "message_end":
                tool_calls = data.get("tool_calls", [])
                if tool_calls:
                    q.put({"type": "message_end", "has_tool_calls": True})

            elif event_type == "file_to_send":
                file_path = data.get("path", "")
                file_name = data.get("file_name", os.path.basename(file_path))
                file_type = data.get("file_type", "file")
                from urllib.parse import quote
                web_url = f"/api/file?path={quote(file_path)}"
                is_image = file_type == "image"
                q.put({
                    "type": "image" if is_image else "file",
                    "content": web_url,
                    "file_name": file_name,
                })

        return on_event

    def upload_file(self):
        """Handle file upload via multipart/form-data. Save to workspace/tmp/ and return metadata."""
        try:
            params = web.input(file={}, session_id="", agent_id="", binding_id="", tenant_id="")
            file_obj = params.get("file")
            session_id = params.get("session_id", "")
            target = _resolve_runtime_target(
                agent_id=params.get("agent_id", ""),
                tenant_id=params.get("tenant_id", ""),
                binding_id=params.get("binding_id", ""),
            )
            if file_obj is None or not hasattr(file_obj, "filename") or not file_obj.filename:
                return json.dumps({"status": "error", "message": "No file uploaded"})

            upload_dir = _get_upload_dir(
                agent_id=target["agent_id"],
                tenant_id=target["tenant_id"],
                binding_id=target["binding_id"],
            )

            original_name = file_obj.filename
            ext = os.path.splitext(original_name)[1].lower()
            safe_name = f"web_{uuid.uuid4().hex[:8]}{ext}"
            save_path = os.path.join(upload_dir, safe_name)

            with open(save_path, "wb") as f:
                f.write(file_obj.read() if hasattr(file_obj, "read") else file_obj.value)

            if ext in IMAGE_EXTENSIONS:
                file_type = "image"
            elif ext in VIDEO_EXTENSIONS:
                file_type = "video"
            else:
                file_type = "file"

            from urllib.parse import quote
            preview_url = f"/api/file?path={quote(save_path)}"

            logger.info(f"[WebChannel] File uploaded: {original_name} -> {save_path} ({file_type})")

            return json.dumps({
                "status": "success",
                "file_path": save_path,
                "file_name": original_name,
                "file_type": file_type,
                "preview_url": preview_url,
                "agent_id": target["agent_id"],
                "tenant_id": target["tenant_id"],
                "binding_id": target["binding_id"],
            }, ensure_ascii=False)

        except Exception as e:
            logger.error(f"[WebChannel] File upload error: {e}", exc_info=True)
            return json.dumps({"status": "error", "message": str(e)})

    def post_message(self):
        """
        Handle incoming messages from users via POST request.
        Returns a request_id for tracking this specific request.
        Supports optional attachments (file paths from /upload).
        """
        try:
            data = web.data()
            json_data = json.loads(data)
            session_id = json_data.get('session_id', f'session_{int(time.time())}')
            prompt = json_data.get('message', '')
            use_sse = json_data.get('stream', True)
            attachments = json_data.get('attachments', [])
            has_enable_thinking = 'enable_thinking' in json_data
            enable_thinking = _parse_bool(json_data.get('enable_thinking'), True)
            target = _resolve_runtime_target(
                agent_id=json_data.get('agent_id', ''),
                tenant_id=json_data.get('tenant_id', ''),
                binding_id=json_data.get('binding_id', ''),
            )
            agent_id = target["agent_id"]
            tenant_id = target["tenant_id"]
            binding_id = target["binding_id"]
            scoped_session_key = self._build_scoped_session_key(session_id, agent_id, tenant_id)

            # Append file references to the prompt (same format as QQ channel)
            if attachments:
                file_refs = []
                for att in attachments:
                    ftype = att.get("file_type", "file")
                    fpath = att.get("file_path", "")
                    if not fpath:
                        continue
                    if ftype == "image":
                        file_refs.append(f"[图片: {fpath}]")
                    elif ftype == "video":
                        file_refs.append(f"[视频: {fpath}]")
                    else:
                        file_refs.append(f"[文件: {fpath}]")
                if file_refs:
                    prompt = prompt + "\n" + "\n".join(file_refs)
                    logger.info(f"[WebChannel] Attached {len(file_refs)} file(s) to message")

            request_id = self._generate_request_id()
            self.request_to_session[request_id] = scoped_session_key

            # Preemption: cancel previous SSE stream for this session
            old_request_id = self.session_to_request.get(scoped_session_key)
            if old_request_id and old_request_id in self.sse_queues:
                old_q = self.sse_queues[old_request_id]
                old_q.put({
                    "type": "cancelled",
                    "content": "Cancelled by newer message",
                    "request_id": old_request_id,
                    "timestamp": time.time()
                })
                logger.info(f"[WebChannel] Cancelled previous SSE stream for session={scoped_session_key}, old_request={old_request_id}")

            # Track the latest request for this session
            self.session_to_request[scoped_session_key] = request_id

            if scoped_session_key not in self.session_queues:
                self.session_queues[scoped_session_key] = Queue()

            if use_sse:
                self.sse_queues[request_id] = Queue()

            trigger_prefixs = conf().get("single_chat_prefix", [""])
            if check_prefix(prompt, trigger_prefixs) is None:
                if trigger_prefixs:
                    prompt = trigger_prefixs[0] + prompt
                    logger.debug(f"[WebChannel] Added prefix to message: {prompt}")

            msg = WebMessage(self._generate_msg_id(), prompt)
            msg.from_user_id = session_id

            context = self._compose_context(ContextType.TEXT, prompt, msg=msg, isgroup=False)

            if context is None:
                logger.warning(f"[WebChannel] Context is None for session {session_id}, message may be filtered")
                if request_id in self.sse_queues:
                    del self.sse_queues[request_id]
                return json.dumps({"status": "error", "message": "Message was filtered"})

            context["session_id"] = session_id
            context["receiver"] = session_id
            context["request_id"] = request_id
            if agent_id:
                context["agent_id"] = agent_id
                context["tenant_id"] = tenant_id
            if binding_id:
                context["binding_id"] = binding_id
            if has_enable_thinking:
                context["enable_thinking"] = enable_thinking

            if use_sse:
                context["on_event"] = self._make_sse_callback(request_id)

            threading.Thread(target=self.produce, args=(context,)).start()

            return json.dumps({"status": "success", "request_id": request_id, "stream": use_sse})

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def stream_response(self, request_id: str):
        """
        SSE generator for a given request_id.
        Yields UTF-8 encoded bytes to avoid WSGI Latin-1 mangling.
        Supports client reconnection: the queue is only removed after a
        "done" event is consumed, so a new GET /stream with the same
        request_id can resume reading remaining events.
        """
        if request_id not in self.sse_queues:
            yield b"data: {\"type\": \"error\", \"message\": \"invalid request_id\"}\n\n"
            return

        q = self.sse_queues[request_id]
        idle_timeout = 600  # 10 minutes without any real event
        deadline = time.time() + idle_timeout
        done = False

        try:
            while time.time() < deadline:
                try:
                    item = q.get(timeout=1)
                except Empty:
                    yield b": keepalive\n\n"
                    continue

                # Real event received, reset idle deadline
                deadline = time.time() + idle_timeout

                payload = json.dumps(item, ensure_ascii=False)
                yield f"data: {payload}\n\n".encode("utf-8")

                if item.get("type") in ("done", "cancelled"):
                    done = True
                    break
        finally:
            if done:
                self.sse_queues.pop(request_id, None)

    def poll_response(self):
        """
        Poll for responses using the session_id.
        """
        try:
            data = web.data()
            json_data = json.loads(data)
            session_id = json_data.get('session_id')
            target = _resolve_runtime_target(
                agent_id=json_data.get('agent_id', ''),
                tenant_id=json_data.get('tenant_id', ''),
                binding_id=json_data.get('binding_id', ''),
            )
            agent_id = target["agent_id"]
            tenant_id = target["tenant_id"]
            scoped_session_key = self._build_scoped_session_key(session_id, agent_id, tenant_id)

            if not session_id or scoped_session_key not in self.session_queues:
                return json.dumps({"status": "error", "message": "Invalid session ID"})

            # 尝试从队列获取响应，不等待
            try:
                # 使用peek而不是get，这样如果前端没有成功处理，下次还能获取到
                response = self.session_queues[scoped_session_key].get(block=False)

                # 返回响应，包含请求ID以区分不同请求
                return json.dumps({
                    "status": "success",
                    "has_content": True,
                    "content": response["content"],
                    "request_id": response["request_id"],
                    "timestamp": response["timestamp"]
                })

            except Empty:
                # 没有新响应
                return json.dumps({"status": "success", "has_content": False})

        except Exception as e:
            logger.error(f"Error polling response: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def chat_page(self):
        """Serve the chat HTML page."""
        return render_chat_html(_FRONTEND_LAYOUT, _frontend_mode(), cache_bust=False)

    def startup(self):
        port = conf().get("web_port", 9899)

        if _is_tenant_auth_enabled():
            logger.info("[WebChannel] 多租户模式已启用：渠道接入只通过租户级渠道配置管理。")
        else:
            logger.info(
                "[WebChannel] 全部可用通道如下，可修改 config.json 配置文件中的 channel_type 字段进行切换，多个通道用逗号分隔：")
            logger.info("[WebChannel]   1. weixin           - 微信")
            logger.info("[WebChannel]   2. web              - 网页")
            logger.info("[WebChannel]   3. terminal         - 终端")
            logger.info("[WebChannel]   4. feishu           - 飞书")
            logger.info("[WebChannel]   5. dingtalk         - 钉钉")
            logger.info("[WebChannel]   6. wecom_bot        - 企微智能机器人")
            logger.info("[WebChannel]   7. wechatcom_app    - 企微自建应用")
            logger.info("[WebChannel]   8. wechatmp         - 个人公众号")
            logger.info("[WebChannel]   9. wechatmp_service - 企业公众号")
        logger.info("[WebChannel] ✅ Web控制台已运行")
        logger.info(f"[WebChannel] 🌐 本地访问: http://localhost:{port}")
        logger.info(f"[WebChannel] 🌍 服务器访问: http://YOUR_IP:{port} (请将YOUR_IP替换为服务器IP)")

        urls = build_web_routes()
        app = web.application(urls, globals(), autoreload=False)

        # 完全禁用web.py的HTTP日志输出
        web.httpserver.LogMiddleware.log = lambda self, status, environ: None

        # 配置web.py的日志级别为ERROR
        logging.getLogger("web").setLevel(logging.ERROR)
        logging.getLogger("web.httpserver").setLevel(logging.ERROR)

        # Build WSGI app with middleware (same as runsimple but without print)
        func = web.httpserver.StaticMiddleware(app.wsgifunc())
        func = web.httpserver.LogMiddleware(func)
        server = web.httpserver.WSGIServer(("0.0.0.0", port), func)
        server.daemon_threads = True
        # Default request_queue_size(5) / timeout(10s) / numthreads(10) are
        # too small: when SSE streams occupy many threads, the backlog fills
        # and new connections get refused (ERR_CONNECTION_ABORTED).
        server.request_queue_size = 128
        server.timeout = 300
        server.requests.min = 20
        server.requests.max = 80
        self._http_server = server
        try:
            server.start()
        except (KeyboardInterrupt, SystemExit):
            server.stop()

    def stop(self):
        if self._http_server:
            try:
                self._http_server.stop()
                logger.info("[WebChannel] HTTP server stopped")
            except Exception as e:
                logger.warning(f"[WebChannel] Error stopping HTTP server: {e}")
            self._http_server = None


def _resolve_frontend_asset(file_path: str):
    return resolve_asset_file(_FRONTEND_LAYOUT, _frontend_mode(), file_path)


globals().update(
    build_core_handlers(
        CoreHandlerDeps(
            check_auth_payload=_check_auth_payload,
            login=_login,
            register=_register,
            logout=_logout,
            require_auth=_require_auth,
            get_upload_dir=_get_upload_dir,
            is_file_allowed=_is_file_access_allowed,
            get_web_channel=WebChannel,
            render_chat_page=lambda: WebChannel().chat_page(),
            resolve_asset_path=_resolve_frontend_asset,
            guess_content_type=guess_content_type,
            logger=logger,
        )
    )
)


def _get_workspace_root(agent_id: str = "", tenant_id: str = "", binding_id: str = ""):
    """解析当前请求对应的工作区目录。"""
    target = _resolve_runtime_target(agent_id=agent_id, tenant_id=tenant_id, binding_id=binding_id)
    if not target["agent_id"]:
        from common.utils import expand_path

        return expand_path(conf().get("agent_workspace", "~/cow"))

    service = _get_agent_service()
    definition = service.resolve_agent(tenant_id=target["tenant_id"], agent_id=target["agent_id"])
    return str(service.get_agent_workspace(definition.tenant_id, definition.agent_id))


def _resolve_agent_definition(agent_id: str = "", tenant_id: str = "", binding_id: str = ""):
    target = _resolve_runtime_target(agent_id=agent_id, tenant_id=tenant_id, binding_id=binding_id)
    if not target["agent_id"]:
        return None
    return _get_agent_service().resolve_agent(
        tenant_id=target["tenant_id"],
        agent_id=target["agent_id"],
        resolve_mcp=True,
    )


def _is_knowledge_enabled(agent_id: str = "", tenant_id: str = "", binding_id: str = "") -> bool:
    definition = _resolve_agent_definition(agent_id=agent_id, tenant_id=tenant_id, binding_id=binding_id)
    if definition is None:
        return bool(conf().get("knowledge", True))
    return bool(definition.knowledge_enabled)


# Route handlers import through delayed dependency wrappers so they can reuse
# the runtime helpers above without creating a circular import during startup.
from channel.web.handlers.channel_admin import ChannelsHandler, WeixinQrHandler
from channel.web.handlers.callbacks import FeishuTenantCallbackHandler, WechatMpTenantCallbackHandler
from channel.web.handlers.configuration import AuthPlatformRegisterHandler, ConfigHandler
from channel.web.handlers.platform import (
    AgentsHandler,
    BindingsHandler,
    PlatformAdminModelDetailHandler,
    PlatformAdminModelsHandler,
    PlatformAdminTenantDetailHandler,
    PlatformAdminTenantsHandler,
    PlatformAgentDetailHandler,
    PlatformAgentsHandler,
    PlatformAvailableModelsHandler,
    PlatformBindingDetailHandler,
    PlatformBindingsHandler,
    PlatformChannelConfigDetailHandler,
    PlatformChannelConfigsHandler,
    PlatformCostsHandler,
    PlatformTenantDetailHandler,
    PlatformTenantModelDetailHandler,
    PlatformTenantModelsHandler,
    PlatformTenantUserDetailHandler,
    PlatformTenantUserIdentitiesHandler,
    PlatformTenantUserIdentityDetailHandler,
    PlatformTenantUserMetaHandler,
    PlatformTenantUsersHandler,
    PlatformTenantsHandler,
    PlatformUsageHandler,
)
from channel.web.handlers.workspace import (
    HistoryHandler,
    KnowledgeGraphHandler,
    KnowledgeListHandler,
    KnowledgeReadHandler,
    LogsHandler,
    MCPServerDetailHandler,
    MCPServerToolsHandler,
    MCPServersHandler,
    MCPServersTestHandler,
    MemoryContentHandler,
    MemoryHandler,
    SchedulerHandler,
    SessionClearContextHandler,
    SessionDetailHandler,
    SessionsHandler,
    SessionTitleHandler,
    SkillsHandler,
    ToolsHandler,
)
