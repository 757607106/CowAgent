import json
import web

from app import _resolve_startup_channels
from channel.web import web_channel
from channel.web.web_channel import ChannelsHandler, PlatformBindingsHandler, WeixinQrHandler
from config import conf


def test_tenant_channel_mode_ignores_legacy_channel_type_entries() -> None:
    assert _resolve_startup_channels(
        "web,weixin,feishu",
        web_console_enabled=True,
        tenant_channel_mode=True,
    ) == ["web"]


def test_legacy_channel_mode_keeps_configured_channels() -> None:
    assert _resolve_startup_channels(
        "web,weixin,feishu",
        web_console_enabled=True,
        tenant_channel_mode=False,
    ) == ["web", "weixin", "feishu"]


def test_channels_handler_hides_global_channels_in_tenant_mode(monkeypatch) -> None:
    monkeypatch.setitem(conf(), "web_tenant_auth", True)
    monkeypatch.setitem(conf(), "channel_type", "web,weixin")

    assert ChannelsHandler._active_channel_set() == {"web"}


def test_global_weixin_qr_is_disabled_in_tenant_mode(monkeypatch) -> None:
    monkeypatch.setitem(conf(), "web_tenant_auth", True)

    payload = json.loads(WeixinQrHandler()._fetch_qr(""))

    assert payload["status"] == "error"
    assert "租户微信渠道配置" in payload["message"]


def test_platform_bindings_get_accepts_missing_channel_config_id(monkeypatch) -> None:
    captured = {}

    class FakeBindingService:
        def list_binding_records(self, **kwargs):
            captured.update(kwargs)
            return []

    monkeypatch.setattr(web_channel, "_require_auth", lambda: None)
    monkeypatch.setattr(web_channel, "_scope_optional_tenant_id", lambda tenant_id: tenant_id)
    monkeypatch.setattr(web_channel, "_get_binding_service", lambda: FakeBindingService())
    monkeypatch.setattr(web_channel.web, "header", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        web_channel.web,
        "input",
        lambda **defaults: web.storage({**defaults, "tenant_id": "psl-tenant"}),
    )

    payload = json.loads(PlatformBindingsHandler().GET())

    assert payload == {"status": "success", "bindings": []}
    assert captured == {
        "tenant_id": "psl-tenant",
        "channel_type": "",
        "channel_config_id": "",
    }
