import json
from pathlib import Path

import pytest

from channel.web.handlers.channel_admin import WeixinQrHandler
from channel.weixin import weixin_api
from channel.weixin.weixin_channel import WeixinChannel
from cow_platform.domain.models import ChannelConfigDefinition
from cow_platform.services.channel_config_service import ChannelConfigService


def _weixin_definition(**overrides):
    data = {
        "tenant_id": "tenant-a",
        "channel_config_id": "chcfg_weixin_a",
        "name": "Tenant A Weixin",
        "channel_type": "weixin",
        "config": {},
        "enabled": True,
    }
    data.update(overrides)
    return ChannelConfigDefinition(**data)


class FakeTenantService:
    def resolve_tenant(self, tenant_id: str):
        return {"tenant_id": tenant_id}


class FakeChannelConfigRepository:
    def __init__(self, definition):
        self.definition = definition
        self.updated_config = None
        self.updated_enabled = None

    def get_channel_config(self, *, channel_config_id: str, tenant_id: str = ""):
        if channel_config_id != self.definition.channel_config_id:
            return None
        if tenant_id and tenant_id != self.definition.tenant_id:
            return None
        return self.definition

    def update_channel_config(self, *, channel_config_id: str, tenant_id: str = "", **updates):
        assert channel_config_id == self.definition.channel_config_id
        assert tenant_id == self.definition.tenant_id
        config = updates.get("config", self.definition.config)
        enabled = updates.get("enabled", self.definition.enabled)
        self.updated_config = dict(config or {})
        self.updated_enabled = enabled
        self.definition = _weixin_definition(config=self.updated_config, enabled=enabled)
        return self.definition

    def export_record(self, definition):
        return {
            "tenant_id": definition.tenant_id,
            "channel_config_id": definition.channel_config_id,
            "name": definition.name,
            "channel_type": definition.channel_type,
            "config": dict(definition.config or {}),
            "enabled": definition.enabled,
            "metadata": dict(definition.metadata or {}),
            "created_by": definition.created_by,
        }


def test_weixin_runtime_overrides_do_not_inject_local_credentials_path() -> None:
    service = ChannelConfigService(tenant_service=FakeTenantService())
    overrides = service.build_runtime_overrides(
        _weixin_definition(config={"weixin_token": "token-from-db"})
    )

    assert overrides["weixin_token"] == "token-from-db"
    assert "weixin_credentials_path" not in overrides


def test_save_weixin_credentials_persists_database_config_without_file_path() -> None:
    repo = FakeChannelConfigRepository(
        _weixin_definition(
            config={
                "weixin_token": "old-token",
                "weixin_credentials_path": "~/.cowagent/weixin/chcfg_weixin_a.json",
            }
        )
    )
    service = ChannelConfigService(repository=repo, tenant_service=FakeTenantService())

    service.save_weixin_credentials(
        channel_config_id="chcfg_weixin_a",
        tenant_id="tenant-a",
        token="new-token",
        base_url="https://tenant.weixin.example",
        bot_id="bot-a",
        user_id="user-a",
    )

    assert repo.updated_enabled is True
    assert repo.updated_config["weixin_token"] == "new-token"
    assert repo.updated_config["weixin_base_url"] == "https://tenant.weixin.example"
    assert repo.updated_config["weixin_bot_id"] == "bot-a"
    assert repo.updated_config["weixin_user_id"] == "user-a"
    assert "weixin_credentials_path" not in repo.updated_config


def test_clear_weixin_credentials_can_remove_secret_token() -> None:
    repo = FakeChannelConfigRepository(
        _weixin_definition(
            config={
                "weixin_token": "expired-token",
                "weixin_base_url": "https://tenant.weixin.example",
                "weixin_bot_id": "bot-a",
                "weixin_user_id": "user-a",
                "weixin_credentials_path": "~/.cowagent/weixin/chcfg_weixin_a.json",
            }
        )
    )
    service = ChannelConfigService(repository=repo, tenant_service=FakeTenantService())

    service.clear_weixin_credentials(channel_config_id="chcfg_weixin_a", tenant_id="tenant-a")

    assert "weixin_token" not in repo.updated_config
    assert repo.updated_config["weixin_base_url"] == "https://tenant.weixin.example"
    assert "weixin_bot_id" not in repo.updated_config
    assert "weixin_user_id" not in repo.updated_config
    assert "weixin_credentials_path" not in repo.updated_config


def test_delete_channel_runtime_artifacts_removes_only_default_weixin_credential_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    default_path = tmp_path / ".cowagent" / "weixin" / "chcfg_weixin_a.json"
    default_path.parent.mkdir(parents=True)
    default_path.write_text(json.dumps({"token": "old"}))
    unsafe_path = tmp_path / "outside.json"
    unsafe_path.write_text(json.dumps({"token": "outside"}))

    service = ChannelConfigService(tenant_service=FakeTenantService())
    deleted = service.delete_channel_runtime_artifacts(
        _weixin_definition(config={"weixin_credentials_path": str(unsafe_path)})
    )

    assert deleted == [str(default_path)]
    assert not default_path.exists()
    assert unsafe_path.exists()


def test_weixin_qr_confirm_saves_tenant_credentials_to_database_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    class FakeWeixinApi:
        def __init__(self, base_url: str):
            self.base_url = base_url

        def poll_qr_status(self, qrcode: str, timeout: int = 10):
            return {
                "status": "confirmed",
                "bot_token": "token-from-qr",
                "ilink_bot_id": "bot-a",
                "baseurl": "https://tenant.weixin.example",
                "ilink_user_id": "user-a",
            }

    class FakeChannelConfigService:
        def __init__(self):
            self.saved = {}

        def resolve_channel_config(self, *, tenant_id: str = "", channel_config_id: str = ""):
            return _weixin_definition(tenant_id=tenant_id, channel_config_id=channel_config_id)

        def save_weixin_credentials(self, **kwargs):
            self.saved.update(kwargs)

    fake_service = FakeChannelConfigService()
    restarted = []
    monkeypatch.setattr(weixin_api, "WeixinApi", FakeWeixinApi)
    monkeypatch.setattr(
        "channel.web.handlers.channel_admin._get_channel_config_service",
        lambda: fake_service,
    )
    monkeypatch.setattr(
        "channel.web.handlers.channel_admin._restart_channel_config_runtime",
        lambda channel_config_id: restarted.append(channel_config_id),
    )
    WeixinQrHandler._qr_state["chcfg_weixin_a"] = {
        "qrcode": "qr-a",
        "qrcode_url": "https://qr.example",
        "base_url": "https://tenant.weixin.example",
        "channel_config_id": "chcfg_weixin_a",
        "tenant_id": "tenant-a",
    }

    payload = json.loads(WeixinQrHandler()._poll_status(channel_config_id="chcfg_weixin_a"))

    assert payload["qr_status"] == "confirmed"
    assert fake_service.saved == {
        "channel_config_id": "chcfg_weixin_a",
        "tenant_id": "tenant-a",
        "token": "token-from-qr",
        "base_url": "https://tenant.weixin.example",
        "bot_id": "bot-a",
        "user_id": "user-a",
    }
    assert restarted == ["chcfg_weixin_a"]
    assert not list((tmp_path / ".cowagent").glob("**/*.json"))


def test_tenant_weixin_channel_expiry_clears_database_token(monkeypatch: pytest.MonkeyPatch) -> None:
    cleared = {}

    class FakeChannelConfigService:
        def clear_weixin_credentials(self, **kwargs):
            cleared.update(kwargs)

    import cow_platform.services.channel_config_service as service_module

    monkeypatch.setattr(service_module, "ChannelConfigService", lambda: FakeChannelConfigService())
    channel = WeixinChannel(_singleton_key="tenant-expiry-test")
    channel.channel_config_id = "chcfg_weixin_a"
    channel.tenant_id = "tenant-a"

    assert channel._relogin() is False
    assert cleared == {"channel_config_id": "chcfg_weixin_a", "tenant_id": "tenant-a"}
    assert channel._stop_event.is_set()
