from types import SimpleNamespace

from channel.web import auth_runtime


def test_auth_token_uses_password_and_expiry_without_global_state() -> None:
    token = auth_runtime.create_auth_token(password="pw", now=100)

    assert auth_runtime.verify_auth_token(token, password="pw", expire_seconds=30, now=120) is True
    assert auth_runtime.verify_auth_token(token, password="pw", expire_seconds=30, now=131) is False
    assert auth_runtime.verify_auth_token(token, password="other", expire_seconds=30, now=120) is False


def test_password_login_sets_password_cookie_and_clears_tenant_cookie(monkeypatch) -> None:
    cookies = []
    monkeypatch.setattr(auth_runtime, "conf", lambda: {"web_password": "secret", "web_session_expire_days": 1})
    monkeypatch.setattr(auth_runtime.web, "setcookie", lambda *args, **kwargs: cookies.append((args, kwargs)))

    result = auth_runtime.login(
        {"password": "secret"},
        tenant_auth_enabled=False,
        auth_service_factory=lambda: None,
    )

    assert result == {"status": "success"}
    assert cookies[0][0][0] == auth_runtime.AUTH_COOKIE
    assert cookies[0][1]["httponly"] is True
    assert cookies[1][0] == (auth_runtime.TENANT_AUTH_COOKIE, "")
    assert cookies[1][1]["expires"] == -1


def test_tenant_auth_payload_reports_bootstrap_and_public_user() -> None:
    session = SimpleNamespace(to_public_dict=lambda: {"tenant_id": "tenant-a"})

    class AuthService:
        def has_credentials(self):
            return False

        def has_platform_admin(self):
            return True

    payload = auth_runtime.build_auth_payload(
        tenant_auth_enabled=True,
        auth_service_factory=AuthService,
        tenant_session=session,
        password_enabled=False,
        password_authenticated=False,
    )

    assert payload["auth_mode"] == "tenant"
    assert payload["authenticated"] is True
    assert payload["bootstrap_required"] is True
    assert payload["platform_bootstrap_required"] is False
    assert payload["user"] == {"tenant_id": "tenant-a"}
