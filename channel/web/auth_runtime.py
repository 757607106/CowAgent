from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Callable

import web

from common.log import logger
from config import conf

AUTH_COOKIE = "cow_auth_token"
TENANT_AUTH_COOKIE = "cow_tenant_auth_token"


def is_password_enabled() -> bool:
    return bool(conf().get("web_password", ""))


def is_tenant_auth_enabled() -> bool:
    return True


def session_expire_seconds() -> int:
    return int(conf().get("web_session_expire_days", 30)) * 86400


def create_auth_token(*, password: str | None = None, now: float | None = None) -> str:
    ts = format(int(now if now is not None else time.time()), "x")
    secret = conf().get("web_password", "") if password is None else password
    sig = hmac.new(secret.encode(), ts.encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def verify_auth_token(
    token: str,
    *,
    password: str | None = None,
    expire_seconds: int | None = None,
    now: float | None = None,
) -> bool:
    if not token or "." not in token:
        return False
    ts_hex, sig = token.split(".", 1)
    try:
        ts = int(ts_hex, 16)
    except ValueError:
        return False
    current_time = now if now is not None else time.time()
    ttl = expire_seconds if expire_seconds is not None else session_expire_seconds()
    if current_time - ts > ttl:
        return False
    secret = conf().get("web_password", "") if password is None else password
    expected = hmac.new(secret.encode(), ts_hex.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


def get_cookie_value(name: str) -> str:
    try:
        cookies = web.cookies()
        return cookies.get(name, "")
    except Exception:
        return ""


def set_auth_cookie(name: str, value: str, *, expire_seconds: int | None = None) -> None:
    web.setcookie(
        name,
        value,
        expires=expire_seconds if expire_seconds is not None else session_expire_seconds(),
        path="/",
        httponly=True,
        samesite="Lax",
    )


def clear_auth_cookie(name: str) -> None:
    web.setcookie(name, "", expires=-1, path="/")


def check_auth(
    *,
    tenant_auth_enabled: bool,
    tenant_session,
    password_enabled: bool,
    password_authenticated: bool,
) -> bool:
    if tenant_auth_enabled:
        return tenant_session is not None
    if not password_enabled:
        return True
    return password_authenticated


def build_auth_payload(
    *,
    tenant_auth_enabled: bool,
    auth_service_factory: Callable[[], object],
    tenant_session,
    password_enabled: bool,
    password_authenticated: bool,
) -> dict[str, object]:
    if tenant_auth_enabled:
        service = auth_service_factory()
        return {
            "status": "success",
            "auth_required": True,
            "auth_mode": "tenant",
            "authenticated": tenant_session is not None,
            "bootstrap_required": not service.has_credentials(),
            "platform_bootstrap_required": not service.has_platform_admin(),
            "user": tenant_session.to_public_dict() if tenant_session else None,
        }
    if not password_enabled:
        return {"status": "success", "auth_required": False, "auth_mode": "none"}
    return {
        "status": "success",
        "auth_required": True,
        "auth_mode": "password",
        "authenticated": password_authenticated,
    }


def login(
    data: dict[str, object],
    *,
    tenant_auth_enabled: bool,
    auth_service_factory: Callable[[], object],
) -> dict[str, object]:
    if tenant_auth_enabled:
        service = auth_service_factory()
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
        set_auth_cookie(TENANT_AUTH_COOKIE, service.create_session_token(session))
        clear_auth_cookie(AUTH_COOKIE)
        return {"status": "success", "user": session.to_public_dict()}

    if not is_password_enabled():
        return {"status": "success"}

    password = str(data.get("password", "") or "")
    expected = conf().get("web_password", "")
    if not hmac.compare_digest(password, expected):
        logger.warning("[WebChannel] Invalid login attempt")
        return {"status": "error", "message": "Wrong password"}

    set_auth_cookie(AUTH_COOKIE, create_auth_token())
    clear_auth_cookie(TENANT_AUTH_COOKIE)
    return {"status": "success"}


def register(
    data: dict[str, object],
    *,
    tenant_auth_enabled: bool,
    auth_service_factory: Callable[[], object],
) -> dict[str, object]:
    if not tenant_auth_enabled:
        return {"status": "error", "message": "tenant auth is disabled"}

    try:
        service = auth_service_factory()
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
        set_auth_cookie(TENANT_AUTH_COOKIE, service.create_session_token(session))
        clear_auth_cookie(AUTH_COOKIE)
        return {"status": "success", **result, "user": session.to_public_dict()}
    except Exception as e:
        logger.warning(f"[WebChannel] Tenant register failed: {e}")
        return {"status": "error", "message": str(e)}


def register_platform_admin(
    data: dict[str, object],
    *,
    tenant_auth_enabled: bool,
    auth_service_factory: Callable[[], object],
) -> dict[str, object]:
    if not tenant_auth_enabled:
        return {"status": "error", "message": "tenant auth is disabled"}

    try:
        service = auth_service_factory()
        result = service.register_platform_admin(
            account=str(data.get("account", "") or ""),
            name=str(data.get("name", "") or data.get("user_name", "") or ""),
            password=str(data.get("password", "") or ""),
        )
        session = service.authenticate_account(
            account=str(data.get("account", "") or ""),
            password=str(data.get("password", "") or ""),
        )
        set_auth_cookie(TENANT_AUTH_COOKIE, service.create_session_token(session))
        clear_auth_cookie(AUTH_COOKIE)
        return {"status": "success", **result, "user": session.to_public_dict()}
    except Exception as e:
        logger.warning(f"[WebChannel] Platform admin register failed: {e}")
        return {"status": "error", "message": str(e)}


def logout() -> None:
    clear_auth_cookie(AUTH_COOKIE)
    clear_auth_cookie(TENANT_AUTH_COOKIE)


def raise_unauthorized() -> None:
    raise web.HTTPError(
        "401 Unauthorized",
        {"Content-Type": "application/json; charset=utf-8"},
        json.dumps({"status": "error", "message": "Unauthorized"}),
    )


def raise_forbidden(message: str = "Forbidden") -> None:
    raise web.HTTPError(
        "403 Forbidden",
        {"Content-Type": "application/json; charset=utf-8"},
        json.dumps({"status": "error", "message": message}, ensure_ascii=False),
    )
