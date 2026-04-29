from __future__ import annotations

import json

import app
import config as config_module
from channel.web import web_channel
from channel.web.handlers import configuration
from config import Config


def test_load_config_uses_env_and_database_without_reading_config_file(monkeypatch) -> None:
    original_config = config_module.config

    def fail_read_file(_path):
        raise AssertionError("platform mode must not read config files")

    def fake_load_platform_settings():
        settings = {"model": "db-model", "web_port": 17777}
        config_module.config.set_platform_settings(settings)
        return settings

    monkeypatch.setattr(config_module, "read_file", fail_read_file)
    monkeypatch.setattr(config_module, "_load_platform_settings_from_database", fake_load_platform_settings)
    monkeypatch.setattr(Config, "load_user_datas", lambda self: None)
    monkeypatch.setenv("AGENT_MAX_STEPS", "9")
    try:
        config_module.load_config()

        assert config_module.conf().get("model") == "db-model"
        assert config_module.conf().get("web_port") == 17777
        assert config_module.conf().get("agent_max_steps") == 9
    finally:
        config_module.config = original_config


def test_platform_settings_override_bootstrap_config_and_env(monkeypatch) -> None:
    cfg = Config(
        {
            "dashscope_api_key": "bootstrap-key",
            "model": "bootstrap-model",
        }
    )
    cfg.set_platform_settings(
        {
            "dashscope_api_key": "database-key",
            "model": "database-model",
        }
    )
    monkeypatch.setattr(config_module, "config", cfg)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "old-env-key")

    assert config_module.conf().get("model") == "database-model"
    assert config_module.conf().get("dashscope_api_key") == "database-key"

    config_module._sync_config_to_environment(force_keys={"dashscope_api_key"})

    assert config_module.os.environ["DASHSCOPE_API_KEY"] == "database-key"


def test_platform_mode_is_always_tenant_mode(monkeypatch) -> None:
    monkeypatch.setitem(config_module.conf(), "web_tenant_auth", False)

    assert app._resolve_startup_channels(web_console_enabled=True) == ["web"]
    assert web_channel._is_tenant_auth_enabled() is True


def test_platform_web_process_does_not_start_channel_runtimes_by_default() -> None:
    cfg = Config(config_module.available_setting)

    assert cfg.get("platform_start_channel_runtimes") is False


def test_platform_mode_disables_legacy_user_data_mutation() -> None:
    cfg = Config({"web_tenant_auth": True})
    user_data = cfg.get_user_data("same-external-user")

    user_data["openai_api_key"] = "tenant-secret"
    user_data["gpt_model"] = "tenant-model"
    user_data.pop("openai_api_key")

    assert cfg.user_datas == {}
    assert cfg.get_user_data("same-external-user").get("openai_api_key") is None
    assert cfg.get_user_data("same-external-user").get("gpt_model") is None


def test_config_handler_writes_platform_settings_not_config_json(monkeypatch) -> None:
    saved = {}

    class FakePlatformConfigService:
        def update_settings(self, updates):
            saved.update(updates)
            return dict(updates)

    monkeypatch.setattr(configuration, "_require_platform_admin", lambda: None)
    monkeypatch.setattr(configuration, "_is_tenant_auth_enabled", lambda: True)
    monkeypatch.setattr(
        configuration,
        "_get_platform_config_service",
        lambda: FakePlatformConfigService(),
    )
    monkeypatch.setattr(configuration.web, "header", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        configuration.web,
        "data",
        lambda: json.dumps(
            {
                "updates": {
                    "model": "qwen3.6-plus",
                    "dashscope_api_key": "db-key",
                    "agent_max_steps": "12",
                }
            }
        ).encode("utf-8"),
    )
    payload = json.loads(configuration.ConfigHandler().POST())

    assert payload["status"] == "success"
    assert saved == {
        "model": "qwen3.6-plus",
        "dashscope_api_key": "db-key",
        "agent_max_steps": 12,
    }
    assert config_module.conf().get("model") == "qwen3.6-plus"
    assert config_module.conf().get("dashscope_api_key") == "db-key"
