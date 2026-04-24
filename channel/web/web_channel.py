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
from collections import OrderedDict
from common import const
from common.log import logger
from common.singleton import singleton
from config import conf
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


def _logout() -> None:
    web.setcookie(_AUTH_COOKIE, "", expires=-1, path="/")
    web.setcookie(_TENANT_AUTH_COOKIE, "", expires=-1, path="/")


def _require_auth():
    """Raise 401 if not authenticated. Call at the top of protected handlers."""
    if not _check_auth():
        raise web.HTTPError("401 Unauthorized",
                            {"Content-Type": "application/json; charset=utf-8"},
                            json.dumps({"status": "error", "message": "Unauthorized"}))


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
    return (tenant_id or "default").strip() or "default"


def _normalize_agent_id(agent_id: str = "") -> str:
    return (agent_id or "default").strip() or "default"


def _normalize_binding_id(binding_id: str = "") -> str:
    return (binding_id or "").strip()


def _scope_tenant_id(tenant_id: str = "", *, default: str = "default") -> str:
    """Resolve a tenant id under the current authenticated tenant session."""
    session = _get_authenticated_tenant_session()
    requested = (tenant_id or "").strip()
    if session:
        if requested and requested != session.tenant_id:
            _raise_forbidden("不能访问其他租户的数据")
        return session.tenant_id
    return _normalize_tenant_id(requested or default)


def _scope_optional_tenant_id(tenant_id: str = "") -> str:
    """Like _scope_tenant_id, but preserves blank tenant filters in legacy mode."""
    session = _get_authenticated_tenant_session()
    requested = (tenant_id or "").strip()
    if session:
        if requested and requested != session.tenant_id:
            _raise_forbidden("不能访问其他租户的数据")
        return session.tenant_id
    return requested


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


def _get_tenant_service():
    from cow_platform.services.tenant_service import TenantService

    return TenantService()


def _get_tenant_user_service():
    from cow_platform.services.tenant_user_service import TenantUserService

    return TenantUserService()


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

        # 打印可用渠道类型提示
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


class ConfigHandler:

    _RECOMMENDED_MODELS = [
        const.MINIMAX_M2_7, const.MINIMAX_M2_5, const.MINIMAX_M2_1, const.MINIMAX_M2_1_LIGHTNING,
        const.GLM_5_TURBO, const.GLM_5, const.GLM_4_7,
        const.QWEN36_PLUS, const.QWEN35_PLUS, const.QWEN3_MAX,
        const.KIMI_K2_5, const.KIMI_K2,
        const.DOUBAO_SEED_2_PRO, const.DOUBAO_SEED_2_CODE,
        const.CLAUDE_4_6_SONNET, const.CLAUDE_4_6_OPUS, const.CLAUDE_4_5_SONNET,
        const.GEMINI_31_FLASH_LITE_PRE, const.GEMINI_31_PRO_PRE, const.GEMINI_3_FLASH_PRE,
        const.GPT_54, const.GPT_54_MINI, const.GPT_54_NANO, const.GPT_5, const.GPT_41, const.GPT_4o,
        const.DEEPSEEK_CHAT, const.DEEPSEEK_REASONER,
    ]

    PROVIDER_MODELS = OrderedDict([
        ("minimax", {
            "label": "MiniMax",
            "api_key_field": "minimax_api_key",
            "api_base_key": None,
            "api_base_default": None,
            "models": [const.MINIMAX_M2_7, const.MINIMAX_M2_7_HIGHSPEED, const.MINIMAX_M2_5, const.MINIMAX_M2_1, const.MINIMAX_M2_1_LIGHTNING],
        }),
        ("zhipu", {
            "label": "智谱AI",
            "api_key_field": "zhipu_ai_api_key",
            "api_base_key": "zhipu_ai_api_base",
            "api_base_default": "https://open.bigmodel.cn/api/paas/v4",
            "models": [const.GLM_5_TURBO, const.GLM_5, const.GLM_4_7],
        }),
        ("dashscope", {
            "label": "通义千问",
            "api_key_field": "dashscope_api_key",
            "api_base_key": None,
            "api_base_default": None,
            "models": [const.QWEN36_PLUS, const.QWEN35_PLUS, const.QWEN3_MAX],
        }),
        ("moonshot", {
            "label": "Kimi",
            "api_key_field": "moonshot_api_key",
            "api_base_key": "moonshot_base_url",
            "api_base_default": "https://api.moonshot.cn/v1",
            "models": [const.KIMI_K2_5, const.KIMI_K2],
        }),
        ("doubao", {
            "label": "豆包",
            "api_key_field": "ark_api_key",
            "api_base_key": "ark_base_url",
            "api_base_default": "https://ark.cn-beijing.volces.com/api/v3",
            "models": [const.DOUBAO_SEED_2_PRO, const.DOUBAO_SEED_2_CODE],
        }),
        ("claudeAPI", {
            "label": "Claude",
            "api_key_field": "claude_api_key",
            "api_base_key": "claude_api_base",
            "api_base_default": "https://api.anthropic.com/v1",
            "models": [const.CLAUDE_4_6_SONNET, const.CLAUDE_4_6_OPUS, const.CLAUDE_4_5_SONNET],
        }),
        ("gemini", {
            "label": "Gemini",
            "api_key_field": "gemini_api_key",
            "api_base_key": "gemini_api_base",
            "api_base_default": "https://generativelanguage.googleapis.com",
            "models": [const.GEMINI_31_FLASH_LITE_PRE, const.GEMINI_31_PRO_PRE, const.GEMINI_3_FLASH_PRE],
        }),
        ("openai", {
            "label": "OpenAI",
            "api_key_field": "open_ai_api_key",
            "api_base_key": "open_ai_api_base",
            "api_base_default": "https://api.openai.com/v1",
            "models": [const.GPT_54, const.GPT_54_MINI, const.GPT_54_NANO, const.GPT_5, const.GPT_41, const.GPT_4o],
        }),
        ("deepseek", {
            "label": "DeepSeek",
            "api_key_field": "deepseek_api_key",
            "api_base_key": "deepseek_api_base",
            "api_base_default": "https://api.deepseek.com/v1",
            "models": [const.DEEPSEEK_CHAT, const.DEEPSEEK_REASONER],
        }),
        ("modelscope", {
            "label": "ModelScope",
            "api_key_field": "modelscope_api_key",
            "api_base_key": None,
            "api_base_default": None,
            "models": [const.QWEN3_5_27B, const.QWEN3_235B_A22B_INSTRUCT_2507],
        }),
        ("linkai", {
            "label": "LinkAI",
            "api_key_field": "linkai_api_key",
            "api_base_key": None,
            "api_base_default": None,
            "models": _RECOMMENDED_MODELS,
        }),
    ])

    EDITABLE_KEYS = {
        "model", "bot_type", "use_linkai",
        "open_ai_api_base", "deepseek_api_base", "claude_api_base", "gemini_api_base",
        "zhipu_ai_api_base", "moonshot_base_url", "ark_base_url",
        "open_ai_api_key", "deepseek_api_key", "claude_api_key", "gemini_api_key",
        "zhipu_ai_api_key", "dashscope_api_key", "moonshot_api_key",
        "ark_api_key", "minimax_api_key", "linkai_api_key", "modelscope_api_key",
        "agent_max_context_tokens", "agent_max_context_turns", "agent_max_steps",
        "enable_thinking", "web_password",
    }

    @staticmethod
    def _mask_key(value: str) -> str:
        """Mask the middle part of an API key for display."""
        if not value or len(value) <= 8:
            return value
        return value[:4] + "*" * (len(value) - 8) + value[-4:]

    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            local_config = conf()
            use_agent = local_config.get("agent", False)
            title = "CowAgent" if use_agent else "AI Assistant"

            api_bases = {}
            api_keys_masked = {}
            for pid, pinfo in self.PROVIDER_MODELS.items():
                base_key = pinfo.get("api_base_key")
                if base_key:
                    api_bases[base_key] = local_config.get(base_key, pinfo["api_base_default"])
                key_field = pinfo.get("api_key_field")
                if key_field and key_field not in api_keys_masked:
                    raw = local_config.get(key_field, "")
                    api_keys_masked[key_field] = self._mask_key(raw) if raw else ""

            providers = {}
            for pid, p in self.PROVIDER_MODELS.items():
                providers[pid] = {
                    "label": p["label"],
                    "models": p["models"],
                    "api_base_key": p["api_base_key"],
                    "api_base_default": p["api_base_default"],
                    "api_key_field": p.get("api_key_field"),
                }

            raw_pwd = local_config.get("web_password", "")
            masked_pwd = ("*" * len(raw_pwd)) if raw_pwd else ""

            return json.dumps({
                "status": "success",
                "use_agent": use_agent,
                "title": title,
                "model": local_config.get("model", ""),
                "bot_type": "openai" if local_config.get("bot_type") == "chatGPT" else local_config.get("bot_type", ""),
                "use_linkai": bool(local_config.get("use_linkai", False)),
                "channel_type": local_config.get("channel_type", ""),
                "agent_max_context_tokens": local_config.get("agent_max_context_tokens", 50000),
                "agent_max_context_turns": local_config.get("agent_max_context_turns", 20),
                "agent_max_steps": local_config.get("agent_max_steps", 20),
                "enable_thinking": bool(local_config.get("enable_thinking", True)),
                "api_bases": api_bases,
                "api_keys": api_keys_masked,
                "providers": providers,
                "web_password_masked": masked_pwd,
            }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            data = json.loads(web.data())
            updates = data.get("updates", {})
            if not updates:
                return json.dumps({"status": "error", "message": "no updates provided"})

            local_config = conf()
            applied = {}
            for key, value in updates.items():
                if key not in self.EDITABLE_KEYS:
                    continue
                if key in ("agent_max_context_tokens", "agent_max_context_turns", "agent_max_steps"):
                    value = int(value)
                if key in ("use_linkai", "enable_thinking"):
                    value = bool(value)
                local_config[key] = value
                applied[key] = value

            if not applied:
                return json.dumps({"status": "error", "message": "no valid keys to update"})

            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))), "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    file_cfg = json.load(f)
            else:
                file_cfg = {}
            file_cfg.update(applied)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(file_cfg, f, indent=4, ensure_ascii=False)

            logger.info(f"[WebChannel] Config updated: {list(applied.keys())}")
            return json.dumps({"status": "success", "applied": applied}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class ChannelsHandler:
    """API for managing external channel configurations (feishu, dingtalk, etc)."""

    CHANNEL_DEFS = OrderedDict([
        ("weixin", {
            "label": {"zh": "微信", "en": "WeChat"},
            "icon": "fa-comment",
            "color": "emerald",
            "fields": [],
        }),
        ("feishu", {
            "label": {"zh": "飞书", "en": "Feishu"},
            "icon": "fa-paper-plane",
            "color": "blue",
            "fields": [
                {"key": "feishu_app_id", "label": "App ID", "type": "text"},
                {"key": "feishu_app_secret", "label": "App Secret", "type": "secret"},
                {"key": "feishu_token", "label": "Verification Token", "type": "secret"},
                {"key": "feishu_bot_name", "label": "Bot Name", "type": "text"},
            ],
        }),
        ("dingtalk", {
            "label": {"zh": "钉钉", "en": "DingTalk"},
            "icon": "fa-comments",
            "color": "blue",
            "fields": [
                {"key": "dingtalk_client_id", "label": "Client ID", "type": "text"},
                {"key": "dingtalk_client_secret", "label": "Client Secret", "type": "secret"},
            ],
        }),
        ("wecom_bot", {
            "label": {"zh": "企微智能机器人", "en": "WeCom Bot"},
            "icon": "fa-robot",
            "color": "emerald",
            "fields": [
                {"key": "wecom_bot_id", "label": "Bot ID", "type": "text"},
                {"key": "wecom_bot_secret", "label": "Secret", "type": "secret"},
            ],
        }),
        ("qq", {
            "label": {"zh": "QQ 机器人", "en": "QQ Bot"},
            "icon": "fa-comment",
            "color": "blue",
            "fields": [
                {"key": "qq_app_id", "label": "App ID", "type": "text"},
                {"key": "qq_app_secret", "label": "App Secret", "type": "secret"},
            ],
        }),
        ("wechatcom_app", {
            "label": {"zh": "企微自建应用", "en": "WeCom App"},
            "icon": "fa-building",
            "color": "emerald",
            "fields": [
                {"key": "wechatcom_corp_id", "label": "Corp ID", "type": "text"},
                {"key": "wechatcomapp_agent_id", "label": "Agent ID", "type": "text"},
                {"key": "wechatcomapp_secret", "label": "Secret", "type": "secret"},
                {"key": "wechatcomapp_token", "label": "Token", "type": "secret"},
                {"key": "wechatcomapp_aes_key", "label": "AES Key", "type": "secret"},
                {"key": "wechatcomapp_port", "label": "Port", "type": "number", "default": 9898},
            ],
        }),
        ("wechatmp", {
            "label": {"zh": "公众号", "en": "WeChat MP"},
            "icon": "fa-comment-dots",
            "color": "emerald",
            "fields": [
                {"key": "wechatmp_app_id", "label": "App ID", "type": "text"},
                {"key": "wechatmp_app_secret", "label": "App Secret", "type": "secret"},
                {"key": "wechatmp_token", "label": "Token", "type": "secret"},
                {"key": "wechatmp_aes_key", "label": "AES Key", "type": "secret"},
                {"key": "wechatmp_port", "label": "Port", "type": "number", "default": 8080},
            ],
        }),
    ])

    @staticmethod
    def _get_weixin_login_status() -> str:
        try:
            import sys
            app_module = sys.modules.get('__main__') or sys.modules.get('app')
            mgr = getattr(app_module, '_channel_mgr', None) if app_module else None
            if mgr:
                ch = mgr.get_channel("weixin")
                if ch and hasattr(ch, 'login_status'):
                    return ch.login_status
        except Exception:
            pass
        return "unknown"

    @staticmethod
    def _mask_secret(value: str) -> str:
        if not value or len(value) <= 8:
            return value
        return value[:4] + "*" * (len(value) - 8) + value[-4:]

    @staticmethod
    def _parse_channel_list(raw) -> list:
        if isinstance(raw, list):
            return [ch.strip() for ch in raw if ch.strip()]
        if isinstance(raw, str):
            return [ch.strip() for ch in raw.split(",") if ch.strip()]
        return []

    @classmethod
    def _active_channel_set(cls) -> set:
        return set(cls._parse_channel_list(conf().get("channel_type", "")))

    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            local_config = conf()
            active_channels = self._active_channel_set()
            channels = []
            for ch_name, ch_def in self.CHANNEL_DEFS.items():
                fields_out = []
                for f in ch_def["fields"]:
                    raw_val = local_config.get(f["key"], f.get("default", ""))
                    if f["type"] == "secret" and raw_val:
                        display_val = self._mask_secret(str(raw_val))
                    else:
                        display_val = raw_val
                    fields_out.append({
                        "key": f["key"],
                        "label": f["label"],
                        "type": f["type"],
                        "value": display_val,
                        "default": f.get("default", ""),
                    })
                ch_info = {
                    "name": ch_name,
                    "label": ch_def["label"],
                    "icon": ch_def["icon"],
                    "color": ch_def["color"],
                    "active": ch_name in active_channels,
                    "fields": fields_out,
                }
                if ch_name == "weixin" and ch_name in active_channels:
                    ch_info["login_status"] = self._get_weixin_login_status()
                channels.append(ch_info)
            return json.dumps({"status": "success", "channels": channels}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Channels API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data())
            action = body.get("action")
            channel_name = body.get("channel")

            if not action or not channel_name:
                return json.dumps({"status": "error", "message": "action and channel required"})

            if channel_name not in self.CHANNEL_DEFS:
                return json.dumps({"status": "error", "message": f"unknown channel: {channel_name}"})

            if action == "save":
                return self._handle_save(channel_name, body.get("config", {}))
            elif action == "connect":
                return self._handle_connect(channel_name, body.get("config", {}))
            elif action == "disconnect":
                return self._handle_disconnect(channel_name)
            else:
                return json.dumps({"status": "error", "message": f"unknown action: {action}"})
        except Exception as e:
            logger.error(f"[WebChannel] Channels POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def _handle_save(self, channel_name: str, updates: dict):
        ch_def = self.CHANNEL_DEFS[channel_name]
        valid_keys = {f["key"] for f in ch_def["fields"]}
        secret_keys = {f["key"] for f in ch_def["fields"] if f["type"] == "secret"}

        local_config = conf()
        applied = {}
        for key, value in updates.items():
            if key not in valid_keys:
                continue
            if key in secret_keys:
                if not value or (len(value) > 8 and "*" * 4 in value):
                    continue
            field_def = next((f for f in ch_def["fields"] if f["key"] == key), None)
            if field_def:
                if field_def["type"] == "number":
                    value = int(value)
                elif field_def["type"] == "bool":
                    value = bool(value)
            local_config[key] = value
            applied[key] = value

        if not applied:
            return json.dumps({"status": "error", "message": "no valid fields to update"})

        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
        else:
            file_cfg = {}
        file_cfg.update(applied)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(file_cfg, f, indent=4, ensure_ascii=False)

        logger.info(f"[WebChannel] Channel '{channel_name}' config updated: {list(applied.keys())}")

        should_restart = False
        active_channels = self._active_channel_set()
        if channel_name in active_channels:
            should_restart = True
            try:
                import sys
                app_module = sys.modules.get('__main__') or sys.modules.get('app')
                mgr = getattr(app_module, '_channel_mgr', None) if app_module else None
                if mgr:
                    threading.Thread(
                        target=mgr.restart,
                        args=(channel_name,),
                        daemon=True,
                    ).start()
                    logger.info(f"[WebChannel] Channel '{channel_name}' restart triggered")
            except Exception as e:
                logger.warning(f"[WebChannel] Failed to restart channel '{channel_name}': {e}")

        return json.dumps({
            "status": "success",
            "applied": list(applied.keys()),
            "restarted": should_restart,
        }, ensure_ascii=False)

    def _handle_connect(self, channel_name: str, updates: dict):
        """Save config fields, add channel to channel_type, and start it."""
        ch_def = self.CHANNEL_DEFS[channel_name]
        valid_keys = {f["key"] for f in ch_def["fields"]}
        secret_keys = {f["key"] for f in ch_def["fields"] if f["type"] == "secret"}

        # Feishu connected via web console must use websocket (long connection) mode
        if channel_name == "feishu":
            updates.setdefault("feishu_event_mode", "websocket")
            valid_keys.add("feishu_event_mode")

        local_config = conf()
        applied = {}
        for key, value in updates.items():
            if key not in valid_keys:
                continue
            if key in secret_keys:
                if not value or (len(value) > 8 and "*" * 4 in value):
                    continue
            field_def = next((f for f in ch_def["fields"] if f["key"] == key), None)
            if field_def:
                if field_def["type"] == "number":
                    value = int(value)
                elif field_def["type"] == "bool":
                    value = bool(value)
            local_config[key] = value
            applied[key] = value

        existing = self._parse_channel_list(conf().get("channel_type", ""))
        if channel_name not in existing:
            existing.append(channel_name)
        new_channel_type = ",".join(existing)
        local_config["channel_type"] = new_channel_type

        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
        else:
            file_cfg = {}
        file_cfg.update(applied)
        file_cfg["channel_type"] = new_channel_type
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(file_cfg, f, indent=4, ensure_ascii=False)

        logger.info(f"[WebChannel] Channel '{channel_name}' connecting, channel_type={new_channel_type}")

        def _do_start():
            try:
                import sys
                app_module = sys.modules.get('__main__') or sys.modules.get('app')
                clear_fn = getattr(app_module, '_clear_singleton_cache', None) if app_module else None
                mgr = getattr(app_module, '_channel_mgr', None) if app_module else None
                if mgr is None:
                    logger.warning(f"[WebChannel] ChannelManager not available, cannot start '{channel_name}'")
                    return
                # Stop existing instance first if still running (e.g. re-connect without disconnect)
                existing_ch = mgr.get_channel(channel_name)
                if existing_ch is not None:
                    logger.info(f"[WebChannel] Stopping existing '{channel_name}' before reconnect...")
                    mgr.stop(channel_name)
                # Always wait for the remote service to release the old connection before
                # establishing a new one (DingTalk drops callbacks on duplicate connections)
                logger.info(f"[WebChannel] Waiting for '{channel_name}' old connection to close...")
                time.sleep(5)
                if clear_fn:
                    clear_fn(channel_name)
                logger.info(f"[WebChannel] Starting channel '{channel_name}'...")
                mgr.start([channel_name], first_start=False)
                logger.info(f"[WebChannel] Channel '{channel_name}' start completed")
            except Exception as e:
                logger.error(f"[WebChannel] Failed to start channel '{channel_name}': {e}",
                             exc_info=True)

        threading.Thread(target=_do_start, daemon=True).start()

        return json.dumps({
            "status": "success",
            "channel_type": new_channel_type,
        }, ensure_ascii=False)

    def _handle_disconnect(self, channel_name: str):
        existing = self._parse_channel_list(conf().get("channel_type", ""))
        existing = [ch for ch in existing if ch != channel_name]
        new_channel_type = ",".join(existing)

        local_config = conf()
        local_config["channel_type"] = new_channel_type

        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
        else:
            file_cfg = {}
        file_cfg["channel_type"] = new_channel_type
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(file_cfg, f, indent=4, ensure_ascii=False)

        def _do_stop():
            try:
                import sys
                app_module = sys.modules.get('__main__') or sys.modules.get('app')
                mgr = getattr(app_module, '_channel_mgr', None) if app_module else None
                clear_fn = getattr(app_module, '_clear_singleton_cache', None) if app_module else None
                if mgr:
                    mgr.stop(channel_name)
                else:
                    logger.warning(f"[WebChannel] ChannelManager not found, cannot stop '{channel_name}'")
                if clear_fn:
                    clear_fn(channel_name)
                logger.info(f"[WebChannel] Channel '{channel_name}' disconnected, "
                            f"channel_type={new_channel_type}")
            except Exception as e:
                logger.warning(f"[WebChannel] Failed to stop channel '{channel_name}': {e}",
                               exc_info=True)

        threading.Thread(target=_do_stop, daemon=True).start()

        return json.dumps({
            "status": "success",
            "channel_type": new_channel_type,
        }, ensure_ascii=False)


class WeixinQrHandler:
    """Handle WeChat QR code login from the web console.

    GET  /api/weixin/qrlogin          → fetch a new QR code
    POST /api/weixin/qrlogin          → poll QR status or start channel after login
    """

    _qr_state = {}

    @staticmethod
    def _qr_to_data_uri(data: str) -> str:
        """Generate a QR code as a PNG data URI."""
        try:
            import qrcode as qr_lib
            import io
            import base64
            qr = qr_lib.QRCode(error_correction=qr_lib.constants.ERROR_CORRECT_L, box_size=6, border=2)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return f"data:image/png;base64,{b64}"
        except ImportError:
            return ""

    @staticmethod
    def _get_running_channel():
        try:
            import sys
            app_module = sys.modules.get('__main__') or sys.modules.get('app')
            mgr = getattr(app_module, '_channel_mgr', None) if app_module else None
            if mgr:
                return mgr.get_channel("weixin")
        except Exception:
            pass
        return None

    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            running_ch = self._get_running_channel()
            if running_ch and hasattr(running_ch, '_current_qr_url') and running_ch._current_qr_url:
                qr_image = self._qr_to_data_uri(running_ch._current_qr_url)
                return json.dumps({
                    "status": "success",
                    "qrcode_url": running_ch._current_qr_url,
                    "qr_image": qr_image,
                    "source": "channel",
                })

            from channel.weixin.weixin_api import WeixinApi, DEFAULT_BASE_URL
            base_url = conf().get("weixin_base_url", DEFAULT_BASE_URL)
            api = WeixinApi(base_url=base_url)
            qr_resp = api.fetch_qr_code()
            qrcode = qr_resp.get("qrcode", "")
            qrcode_url = qr_resp.get("qrcode_img_content", "")
            if not qrcode:
                return json.dumps({"status": "error", "message": "No QR code returned"})
            qr_image = self._qr_to_data_uri(qrcode_url)
            WeixinQrHandler._qr_state = {
                "qrcode": qrcode,
                "qrcode_url": qrcode_url,
                "base_url": base_url,
            }
            return json.dumps({"status": "success", "qrcode_url": qrcode_url, "qr_image": qr_image})
        except Exception as e:
            logger.error(f"[WebChannel] WeixinQr GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data())
            action = body.get("action", "poll")

            if action == "poll":
                return self._poll_status()
            elif action == "refresh":
                return self.GET()
            else:
                return json.dumps({"status": "error", "message": f"unknown action: {action}"})
        except Exception as e:
            logger.error(f"[WebChannel] WeixinQr POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def _poll_status(self):
        state = WeixinQrHandler._qr_state
        qrcode = state.get("qrcode", "")
        base_url = state.get("base_url", "")
        if not qrcode:
            return json.dumps({"status": "error", "message": "No active QR session"})

        from channel.weixin.weixin_api import WeixinApi, DEFAULT_BASE_URL
        api = WeixinApi(base_url=base_url or DEFAULT_BASE_URL)
        try:
            status_resp = api.poll_qr_status(qrcode, timeout=10)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

        qr_status = status_resp.get("status", "wait")

        if qr_status == "confirmed":
            bot_token = status_resp.get("bot_token", "")
            bot_id = status_resp.get("ilink_bot_id", "")
            result_base_url = status_resp.get("baseurl", base_url)
            user_id = status_resp.get("ilink_user_id", "")

            if not bot_token or not bot_id:
                return json.dumps({"status": "error", "message": "Login confirmed but missing token"})

            cred_path = os.path.expanduser(
                conf().get("weixin_credentials_path", "~/.weixin_cow_credentials.json")
            )
            from channel.weixin.weixin_channel import _save_credentials
            _save_credentials(cred_path, {
                "token": bot_token,
                "base_url": result_base_url,
                "bot_id": bot_id,
                "user_id": user_id,
            })
            conf()["weixin_token"] = bot_token
            conf()["weixin_base_url"] = result_base_url

            WeixinQrHandler._qr_state = {}
            logger.info(f"[WebChannel] WeChat QR login confirmed: bot_id={bot_id}")

            return json.dumps({
                "status": "success",
                "qr_status": "confirmed",
                "bot_id": bot_id,
            })

        if qr_status == "expired":
            new_resp = api.fetch_qr_code()
            new_qrcode = new_resp.get("qrcode", "")
            new_qrcode_url = new_resp.get("qrcode_img_content", "")
            new_qr_image = self._qr_to_data_uri(new_qrcode_url)
            WeixinQrHandler._qr_state["qrcode"] = new_qrcode
            WeixinQrHandler._qr_state["qrcode_url"] = new_qrcode_url
            return json.dumps({
                "status": "success",
                "qr_status": "expired",
                "qrcode_url": new_qrcode_url,
                "qr_image": new_qr_image,
            })

        return json.dumps({"status": "success", "qr_status": qr_status})


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
    )


def _is_knowledge_enabled(agent_id: str = "", tenant_id: str = "", binding_id: str = "") -> bool:
    definition = _resolve_agent_definition(agent_id=agent_id, tenant_id=tenant_id, binding_id=binding_id)
    if definition is None:
        return bool(conf().get("knowledge", True))
    return bool(definition.knowledge_enabled)


class AgentsHandler:
    """Simple agent listing API – also enforces tenant isolation via _scope_optional_tenant_id."""

    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', channel_type='')
            service = _get_agent_service()
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            return json.dumps(
                {"status": "success", "agents": service.list_agent_records(tenant_id or 'default')},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] Agents API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class PlatformTenantUserMetaHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from cow_platform.services.tenant_user_service import TenantUserService

            return json.dumps(
                {
                    "status": "success",
                    "roles": list(TenantUserService.list_roles()),
                    "statuses": list(TenantUserService.list_statuses()),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUserMeta GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class PlatformTenantsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            service = _get_tenant_service()
            session = _get_authenticated_tenant_session()
            if session:
                definition = service.resolve_tenant(session.tenant_id)
                tenants = [service.serialize_tenant(definition)]
            else:
                tenants = service.list_tenant_records()
            return json.dumps(
                {"status": "success", "tenants": tenants},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenants GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_tenant_service()
            result = service.create_tenant(
                tenant_id=_scope_tenant_id(str(body.get("tenant_id", "")).strip()),
                name=str(body.get("name", "")).strip(),
                status=str(body.get("status", "active")).strip() or "active",
                metadata=body.get("metadata", {}),
            )
            _get_agent_service().ensure_default_agent(result["tenant_id"])
            return json.dumps({"status": "success", "tenant": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenants POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class PlatformTenantDetailHandler:
    def GET(self, tenant_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            service = _get_tenant_service()
            scoped_tenant_id = _scope_tenant_id(str(tenant_id).strip())
            definition = service.resolve_tenant(scoped_tenant_id)
            return json.dumps(
                {"status": "success", "tenant": service.serialize_tenant(definition)},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantDetail GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def PUT(self, tenant_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_tenant_service()
            scoped_tenant_id = _scope_tenant_id(str(tenant_id).strip())
            result = service.update_tenant(
                tenant_id=scoped_tenant_id,
                name=body.get("name"),
                status=body.get("status"),
                metadata=body.get("metadata"),
            )
            return json.dumps({"status": "success", "tenant": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantDetail PUT error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class PlatformTenantUsersHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', role='', status='')
            service = _get_tenant_user_service()
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            return json.dumps(
                {
                    "status": "success",
                    "tenant_users": service.list_user_records(
                        tenant_id=tenant_id,
                        role=(params.role or "").strip(),
                        status=(params.status or "").strip(),
                    ),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUsers GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_tenant_user_service()
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "")).strip())
            result = service.create_user(
                tenant_id=tenant_id,
                user_id=str(body.get("user_id", "")).strip(),
                account=str(body.get("account", "")).strip(),
                name=str(body.get("name", "")).strip(),
                role=str(body.get("role", "member")).strip() or "member",
                status=str(body.get("status", "active")).strip() or "active",
                password=str(body.get("password", "")).strip(),
                metadata=body.get("metadata", {}),
            )
            return json.dumps({"status": "success", "tenant_user": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUsers POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class PlatformTenantUserDetailHandler:
    def GET(self, tenant_id, user_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            service = _get_tenant_user_service()
            scoped_tenant_id = _scope_tenant_id(str(tenant_id).strip())
            definition = service.resolve_user(tenant_id=scoped_tenant_id, user_id=str(user_id).strip())
            return json.dumps(
                {"status": "success", "tenant_user": service.serialize_user(definition)},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUserDetail GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def PUT(self, tenant_id, user_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_tenant_user_service()
            scoped_tenant_id = _scope_tenant_id(str(tenant_id).strip())
            result = service.update_user(
                tenant_id=scoped_tenant_id,
                user_id=str(user_id).strip(),
                name=body.get("name"),
                role=body.get("role"),
                status=body.get("status"),
                metadata=body.get("metadata"),
            )
            return json.dumps({"status": "success", "tenant_user": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUserDetail PUT error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def DELETE(self, tenant_id, user_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            service = _get_tenant_user_service()
            scoped_tenant_id = _scope_tenant_id(str(tenant_id).strip())
            result = service.delete_user(
                tenant_id=scoped_tenant_id,
                user_id=str(user_id).strip(),
            )
            return json.dumps({"status": "success", "tenant_user": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUserDetail DELETE error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class PlatformTenantUserIdentitiesHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', user_id='', channel_type='')
            service = _get_tenant_user_service()
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            return json.dumps(
                {
                    "status": "success",
                    "identities": service.list_identity_records(
                        tenant_id=tenant_id,
                        user_id=(params.user_id or "").strip(),
                        channel_type=(params.channel_type or "").strip(),
                    ),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUserIdentities GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_tenant_user_service()
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "")).strip())
            result = service.bind_identity(
                tenant_id=tenant_id,
                user_id=str(body.get("user_id", "")).strip(),
                channel_type=str(body.get("channel_type", "")).strip(),
                external_user_id=str(body.get("external_user_id", "")).strip(),
                metadata=body.get("metadata", {}),
            )
            return json.dumps({"status": "success", "identity": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUserIdentities POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class PlatformTenantUserIdentityDetailHandler:
    def DELETE(self, tenant_id, channel_type, external_user_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            service = _get_tenant_user_service()
            scoped_tenant_id = _scope_tenant_id(str(tenant_id).strip())
            result = service.unbind_identity(
                tenant_id=scoped_tenant_id,
                channel_type=str(channel_type).strip(),
                external_user_id=str(external_user_id).strip(),
            )
            return json.dumps({"status": "success", "identity": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformTenantUserIdentityDetail DELETE error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class PlatformAgentsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='default')
            service = _get_agent_service()
            tenant_id = _scope_tenant_id(params.tenant_id)
            return json.dumps(
                {"status": "success", "agents": service.list_agent_records(tenant_id)},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAgents GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_agent_service()
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "default")).strip())
            result = service.create_agent(
                tenant_id=tenant_id,
                agent_id=(body.get("agent_id") or None),
                name=str(body.get("name", "")),
                model=str(body.get("model", "")),
                system_prompt=str(body.get("system_prompt", "")),
                tools=body.get("tools", []),
                skills=body.get("skills", []),
                knowledge_enabled=bool(body.get("knowledge_enabled", False)),
                mcp_servers=body.get("mcp_servers", {}),
            )
            return json.dumps({"status": "success", "agent": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAgents POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class PlatformAgentDetailHandler:
    def GET(self, agent_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='default')
            tenant_id = _scope_tenant_id(params.tenant_id)
            service = _get_agent_service()
            definition = service.resolve_agent(tenant_id=tenant_id, agent_id=agent_id)
            return json.dumps(
                {"status": "success", "agent": service.serialize_agent(definition)},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAgentDetail GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def PUT(self, agent_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_agent_service()
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "default")).strip())
            result = service.update_agent(
                agent_id=agent_id,
                tenant_id=tenant_id,
                name=body.get("name"),
                model=body.get("model"),
                system_prompt=body.get("system_prompt"),
                tools=body.get("tools"),
                skills=body.get("skills"),
                knowledge_enabled=body.get("knowledge_enabled"),
                mcp_servers=body.get("mcp_servers"),
            )
            # Agent runtime capability boundary changed (prompt/tools/skills/mcp/knowledge):
            # clear cached instances so next request always re-initializes with latest config.
            try:
                from bridge.bridge import Bridge
                Bridge().get_agent_bridge().clear_agent_sessions(tenant_id=tenant_id, agent_id=agent_id)
            except Exception as clear_err:
                logger.warning(
                    f"[WebChannel] Failed to clear cached sessions after agent update "
                    f"({tenant_id}/{agent_id}): {clear_err}"
                )
            return json.dumps({"status": "success", "agent": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAgentDetail PUT error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def DELETE(self, agent_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='default')
            tenant_id = _scope_tenant_id(params.tenant_id)
            service = _get_agent_service()
            deleted = service.delete_agent(agent_id=agent_id, tenant_id=tenant_id)
            try:
                from bridge.bridge import Bridge
                Bridge().get_agent_bridge().clear_agent_sessions(tenant_id=tenant_id, agent_id=agent_id)
            except Exception:
                pass

            return json.dumps(
                {"status": "success", "agent": deleted, "agent_id": agent_id},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformAgentDetail DELETE error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class BindingsHandler:
    """Simple binding listing API – also enforces tenant isolation via _scope_optional_tenant_id."""

    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', channel_type='')
            service = _get_binding_service()
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            return json.dumps(
                {
                    "status": "success",
                    "bindings": service.list_binding_records(
                        tenant_id=tenant_id,
                        channel_type=(params.channel_type or "").strip(),
                    ),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] Bindings API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class PlatformBindingsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', channel_type='')
            service = _get_binding_service()
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            return json.dumps(
                {
                    "status": "success",
                    "bindings": service.list_binding_records(
                        tenant_id=tenant_id,
                        channel_type=(params.channel_type or "").strip(),
                    ),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformBindings GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_binding_service()
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "default")).strip())
            result = service.create_binding(
                tenant_id=tenant_id,
                binding_id=str(body.get("binding_id", "")),
                name=str(body.get("name", "")),
                channel_type=str(body.get("channel_type", "")),
                agent_id=str(body.get("agent_id", "")),
                enabled=bool(body.get("enabled", True)),
                metadata=body.get("metadata", {}),
            )
            return json.dumps({"status": "success", "binding": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformBindings POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class PlatformBindingDetailHandler:
    def GET(self, binding_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='')
            service = _get_binding_service()
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            definition = service.resolve_binding(binding_id=binding_id, tenant_id=tenant_id)
            return json.dumps(
                {"status": "success", "binding": service.serialize_binding(definition)},
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] PlatformBindingDetail GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def PUT(self, binding_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            service = _get_binding_service()
            tenant_id = _scope_optional_tenant_id(body.get("tenant_id", "") or "")
            result = service.update_binding(
                binding_id=binding_id,
                tenant_id=tenant_id,
                name=body.get("name"),
                channel_type=body.get("channel_type"),
                agent_id=body.get("agent_id"),
                enabled=body.get("enabled"),
                metadata=body.get("metadata"),
            )
            return json.dumps({"status": "success", "binding": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformBindingDetail PUT error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def DELETE(self, binding_id):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='')
            service = _get_binding_service()
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            result = service.delete_binding(binding_id=binding_id, tenant_id=tenant_id)
            return json.dumps({"status": "success", "binding": result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformBindingDetail DELETE error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class PlatformUsageHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', agent_id='', day='', request_id='', limit='100')
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            usage = _get_usage_service().list_usage_records(
                tenant_id=tenant_id,
                agent_id=(params.agent_id or "").strip(),
                day=(params.day or "").strip(),
                request_id=(params.request_id or "").strip(),
                limit=int(params.limit or 100),
            )
            return json.dumps({"status": "success", "usage": usage}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformUsage GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class PlatformCostsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='', agent_id='', day='')
            tenant_id = _scope_optional_tenant_id(params.tenant_id)
            summary = _get_usage_service().summarize_usage(
                tenant_id=tenant_id,
                agent_id=(params.agent_id or "").strip(),
                day=(params.day or "").strip(),
            )
            return json.dumps({"status": "success", "summary": summary}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] PlatformCosts GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class ToolsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.tools.tool_manager import ToolManager
            tm = ToolManager()
            if not tm.tool_classes:
                tm.load_tools()
            tools = []
            for name, cls in tm.tool_classes.items():
                try:
                    instance = cls()
                    tools.append({
                        "name": name,
                        "description": instance.description,
                    })
                except Exception:
                    tools.append({"name": name, "description": ""})
            try:
                from agent.tools.memory.memory_search import MemorySearchTool
                from agent.tools.memory.memory_get import MemoryGetTool
                existing_names = {item.get("name") for item in tools}
                for cls in (MemorySearchTool, MemoryGetTool):
                    if cls.name not in existing_names:
                        tools.append({
                            "name": cls.name,
                            "description": cls.description,
                        })
            except Exception as e:
                logger.debug(f"[WebChannel] Memory tool metadata unavailable: {e}")
            return json.dumps({"status": "success", "tools": tools}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Tools API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class SkillsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.skills.service import SkillService
            from agent.skills.manager import SkillManager
            params = web.input(agent_id='', binding_id='', tenant_id='')
            workspace_root = _get_workspace_root(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            manager = SkillManager(custom_dir=os.path.join(workspace_root, "skills"))
            service = SkillService(manager)
            skills = service.query()
            return json.dumps({"status": "success", "skills": skills}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Skills API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.skills.service import SkillService
            from agent.skills.manager import SkillManager
            body = json.loads(web.data())
            action = body.get("action")
            name = body.get("name")
            if not action or not name:
                return json.dumps({"status": "error", "message": "action and name are required"})
            workspace_root = _get_workspace_root(
                agent_id=body.get("agent_id", ""),
                tenant_id=body.get("tenant_id", ""),
                binding_id=body.get("binding_id", ""),
            )
            manager = SkillManager(custom_dir=os.path.join(workspace_root, "skills"))
            service = SkillService(manager)
            if action == "open":
                service.open({"name": name})
            elif action == "close":
                service.close({"name": name})
            elif action == "delete":
                service.delete({"name": name})
            else:
                return json.dumps({"status": "error", "message": f"unknown action: {action}"})
            return json.dumps({"status": "success"}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Skills POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class MemoryHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.memory.service import MemoryService
            params = web.input(page='1', page_size='20', category='memory', agent_id='', binding_id='', tenant_id='')
            workspace_root = _get_workspace_root(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            service = MemoryService(workspace_root)
            result = service.list_files(
                page=int(params.page), page_size=int(params.page_size),
                category=params.category,
            )
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Memory API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class MemoryContentHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.memory.service import MemoryService
            params = web.input(filename='', category='memory', agent_id='', binding_id='', tenant_id='')
            if not params.filename:
                return json.dumps({"status": "error", "message": "filename required"})
            workspace_root = _get_workspace_root(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            service = MemoryService(workspace_root)
            result = service.get_content(params.filename, category=params.category)
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except ValueError:
            return json.dumps({"status": "error", "message": "invalid filename"})
        except FileNotFoundError:
            return json.dumps({"status": "error", "message": "file not found"})
        except Exception as e:
            logger.error(f"[WebChannel] Memory content API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class SchedulerHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.tools.scheduler.task_store import TaskStore
            params = web.input(agent_id='', binding_id='', tenant_id='')
            workspace_root = _get_workspace_root(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            store_path = os.path.join(workspace_root, "scheduler", "tasks.json")
            store = TaskStore(store_path)
            tasks = store.list_tasks()
            return json.dumps({"status": "success", "tasks": tasks}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Scheduler API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class SessionsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(page='1', page_size='50', agent_id='', binding_id='', tenant_id='')
            target = _resolve_runtime_target(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            if target["agent_id"]:
                repository = _get_session_repository()
                result = repository.list_sessions(
                    tenant_id=target["tenant_id"],
                    agent_id=target["agent_id"],
                    channel_type="web",
                    page=int(params.page),
                    page_size=int(params.page_size),
                )
            else:
                store = _get_session_store()
                result = store.list_sessions(
                    channel_type="web",
                    page=int(params.page),
                    page_size=int(params.page_size),
                )
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Sessions API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class SessionDetailHandler:
    def DELETE(self, session_id: str):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        logger.info(f"[WebChannel] DELETE session request: {session_id}")
        try:
            if not session_id:
                return json.dumps({"status": "error", "message": "session_id required"})
            params = web.input(agent_id='', binding_id='', tenant_id='')
            target = _resolve_runtime_target(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            tenant_id = target["tenant_id"]
            agent_id = target["agent_id"]

            if agent_id:
                repository = _get_session_repository()
                repository.clear_session(tenant_id, agent_id, session_id)
            else:
                _get_session_store().clear_session(session_id)

            # Also remove the Agent instance from AgentBridge if exists
            try:
                from bridge.bridge import Bridge
                ab = Bridge().get_agent_bridge()
                if agent_id:
                    cache_key = _get_runtime_adapter().build_cache_session_key(tenant_id, agent_id, session_id)
                    ab.clear_session(session_id=session_id, cache_key=cache_key)
                    logger.info(f"[WebChannel] Removed agent instance for session {cache_key}")
                else:
                    ab.clear_session(session_id=session_id)
                    logger.info(f"[WebChannel] Removed agent instance for session {session_id}")
            except Exception:
                pass

            channel = WebChannel()
            channel.session_queues.pop(channel._build_scoped_session_key(session_id, agent_id, tenant_id), None)

            logger.info(f"[WebChannel] Session deleted: {session_id}")
            return json.dumps({"status": "success"})
        except Exception as e:
            logger.error(f"[WebChannel] Session delete error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def PUT(self, session_id: str):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            if not session_id:
                return json.dumps({"status": "error", "message": "session_id required"})
            body = json.loads(web.data())
            title = body.get("title", "").strip()
            if not title:
                return json.dumps({"status": "error", "message": "title required"})
            target = _resolve_runtime_target(
                agent_id=body.get("agent_id", ""),
                tenant_id=body.get("tenant_id", ""),
                binding_id=body.get("binding_id", ""),
            )

            if target["agent_id"]:
                repository = _get_session_repository()
                found = repository.rename_session(target["tenant_id"], target["agent_id"], session_id, title)
            else:
                found = _get_session_store().rename_session(session_id, title)
            if not found:
                return json.dumps({"status": "error", "message": "session not found"})
            return json.dumps({"status": "success"})
        except Exception as e:
            logger.error(f"[WebChannel] Session rename error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class SessionTitleHandler:
    def POST(self, session_id: str):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            if not session_id:
                return json.dumps({"status": "error", "message": "session_id required"})

            body = json.loads(web.data())
            user_message = body.get("user_message", "")
            assistant_reply = body.get("assistant_reply", "")
            target = _resolve_runtime_target(
                agent_id=body.get("agent_id", ""),
                tenant_id=body.get("tenant_id", ""),
                binding_id=body.get("binding_id", ""),
            )
            if not user_message:
                return json.dumps({"status": "error", "message": "user_message required"})

            title = _generate_session_title(user_message, assistant_reply)

            if target["agent_id"]:
                repository = _get_session_repository()
                updated = repository.rename_session(target["tenant_id"], target["agent_id"], session_id, title)
            else:
                updated = _get_session_store().rename_session(session_id, title)
            logger.info(f"[WebChannel] Session title set: sid={session_id}, title='{title}', db_updated={updated}")

            return json.dumps({"status": "success", "title": title}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Title generation error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class SessionClearContextHandler:
    def POST(self, session_id: str):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            if not session_id:
                return json.dumps({"status": "error", "message": "session_id required"})
            params = web.input(agent_id='', binding_id='', tenant_id='')
            target = _resolve_runtime_target(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            tenant_id = target["tenant_id"]
            agent_id = target["agent_id"]

            if agent_id:
                repository = _get_session_repository()
                new_seq = repository.clear_context(tenant_id, agent_id, session_id)
            else:
                new_seq = _get_session_store().clear_context(session_id)

            # Delete the agent instance so a fresh one is created on the next message
            try:
                from bridge.bridge import Bridge
                bridge = Bridge()
                ab = bridge.get_agent_bridge()
                if agent_id:
                    cache_key = _get_runtime_adapter().build_cache_session_key(tenant_id, agent_id, session_id)
                    ab.clear_session(session_id=session_id, cache_key=cache_key)
                    logger.info(f"[WebChannel] Cleared agent instance for session {cache_key}")
                else:
                    ab.clear_session(session_id=session_id)
                    logger.info(f"[WebChannel] Cleared agent instance for session {session_id}")
            except Exception:
                pass

            return json.dumps({"status": "success", "context_start_seq": new_seq})
        except Exception as e:
            logger.error(f"[WebChannel] Clear context error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class HistoryHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        web.header('Access-Control-Allow-Origin', '*')
        try:
            params = web.input(session_id='', page='1', page_size='20', agent_id='', binding_id='', tenant_id='')
            session_id = params.session_id.strip()
            if not session_id:
                return json.dumps({"status": "error", "message": "session_id required"})
            target = _resolve_runtime_target(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            if target["agent_id"]:
                repository = _get_session_repository()
                result = repository.load_history_page(
                    tenant_id=target["tenant_id"],
                    agent_id=target["agent_id"],
                    session_id=session_id,
                    page=int(params.page),
                    page_size=int(params.page_size),
                )
            else:
                store = _get_session_store()
                result = store.load_history_page(
                    session_id=session_id,
                    page=int(params.page),
                    page_size=int(params.page_size),
                )
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] History API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class LogsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'text/event-stream; charset=utf-8')
        web.header('Cache-Control', 'no-cache')
        web.header('X-Accel-Buffering', 'no')

        from config import get_root
        log_path = os.path.join(get_root(), "run.log")

        def generate():
            if not os.path.isfile(log_path):
                yield b"data: {\"type\": \"error\", \"message\": \"run.log not found\"}\n\n"
                return

            # Read last 200 lines for initial display
            try:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                tail_lines = lines[-200:]
                chunk = ''.join(tail_lines)
                payload = json.dumps({"type": "init", "content": chunk}, ensure_ascii=False)
                yield f"data: {payload}\n\n".encode('utf-8')
            except Exception as e:
                yield f"data: {{\"type\": \"error\", \"message\": \"{e}\"}}\n\n".encode('utf-8')
                return

            # Tail new lines
            try:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    f.seek(0, 2)  # seek to end
                    deadline = time.time() + 600  # 10 min max
                    while time.time() < deadline:
                        line = f.readline()
                        if line:
                            payload = json.dumps({"type": "line", "content": line}, ensure_ascii=False)
                            yield f"data: {payload}\n\n".encode('utf-8')
                        else:
                            yield b": keepalive\n\n"
                            time.sleep(1)
            except GeneratorExit:
                return
            except Exception:
                return

        return generate()


class KnowledgeListHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.knowledge.service import KnowledgeService
            params = web.input(agent_id='', binding_id='', tenant_id='')
            knowledge_enabled = _is_knowledge_enabled(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            svc = KnowledgeService(
                _get_workspace_root(
                    agent_id=params.agent_id,
                    tenant_id=params.tenant_id,
                    binding_id=params.binding_id,
                ),
                enabled=knowledge_enabled,
            )
            result = svc.list_tree()
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Knowledge list error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class KnowledgeReadHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.knowledge.service import KnowledgeService
            params = web.input(path='', agent_id='', binding_id='', tenant_id='')
            knowledge_enabled = _is_knowledge_enabled(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            svc = KnowledgeService(
                _get_workspace_root(
                    agent_id=params.agent_id,
                    tenant_id=params.tenant_id,
                    binding_id=params.binding_id,
                ),
                enabled=knowledge_enabled,
            )
            result = svc.read_file(params.path)
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except (ValueError, FileNotFoundError, RuntimeError) as e:
            return json.dumps({"status": "error", "message": str(e)})
        except Exception as e:
            logger.error(f"[WebChannel] Knowledge read error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class KnowledgeGraphHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.knowledge.service import KnowledgeService
            params = web.input(agent_id='', binding_id='', tenant_id='')
            knowledge_enabled = _is_knowledge_enabled(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            svc = KnowledgeService(
                _get_workspace_root(
                    agent_id=params.agent_id,
                    tenant_id=params.tenant_id,
                    binding_id=params.binding_id,
                ),
                enabled=knowledge_enabled,
            )
            return json.dumps(svc.build_graph(), ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Knowledge graph error: {e}")
            return json.dumps({"nodes": [], "links": [], "enabled": False})


class MCPServersHandler:
    """GET /api/mcp/servers — list MCP servers from the current agent definition."""

    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(agent_id='', tenant_id='')
            tenant_id = _scope_tenant_id(params.tenant_id)
            agent_id = _normalize_agent_id(params.agent_id)

            from cow_platform.services.agent_service import AgentService
            from cow_platform.repositories.agent_repository import AgentRepository
            service = AgentService(AgentRepository())
            definition = service.resolve_agent(tenant_id=tenant_id, agent_id=agent_id)

            servers = []
            for name, config in definition.mcp_servers.items():
                servers.append({
                    "name": name,
                    "command": config.get("command", ""),
                    "args": config.get("args", []),
                    "env": config.get("env", {}),
                    "enabled": config.get("enabled", True),
                })
            return json.dumps({"status": "success", "servers": servers}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] MCP servers list error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class MCPServersTestHandler:
    """POST /api/mcp/servers/test — test connectivity to an MCP server."""

    def POST(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data())
            command = body.get("command", "")
            args = body.get("args", [])
            env = body.get("env", None)

            if not command:
                return json.dumps({"status": "error", "message": "command is required"})

            import asyncio
            from agent.tools.mcp.mcp_manager import MCPManager
            manager = MCPManager()
            result = asyncio.run(manager.test_connection(command, args, env))
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] MCP server test error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


class MCPServerToolsHandler:
    """GET /api/mcp/servers/{name}/tools — list tools from a specific MCP server."""

    def GET(self, server_name):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(agent_id='', tenant_id='')
            tenant_id = _scope_tenant_id(params.tenant_id)
            agent_id = _normalize_agent_id(params.agent_id)

            definition = _get_agent_service().resolve_agent(tenant_id=tenant_id, agent_id=agent_id)
            server_config = dict(definition.mcp_servers or {}).get(server_name)
            if not isinstance(server_config, dict):
                return json.dumps({
                    "status": "error",
                    "message": f"MCP server '{server_name}' not found for agent {tenant_id}/{agent_id}",
                })

            import asyncio
            from agent.tools.mcp.mcp_manager import MCPManager

            manager = MCPManager()
            result = asyncio.run(manager.test_connection(
                command=str(server_config.get("command", "") or ""),
                args=list(server_config.get("args", []) or []),
                env=server_config.get("env", None),
            ))
            if not result.get("success"):
                return json.dumps({
                    "status": "error",
                    "message": result.get("error") or f"MCP server '{server_name}' not available",
                    "tools": [],
                }, ensure_ascii=False)
            tool_list = result.get("tools", [])
            return json.dumps({"status": "success", "tools": tool_list}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] MCP server tools error: {e}")
            return json.dumps({"status": "error", "message": str(e)})
