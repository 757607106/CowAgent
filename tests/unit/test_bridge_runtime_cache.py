from bridge.bridge import Bridge
from cow_platform.runtime.scope import activate_config_overrides


def test_runtime_bot_cache_key_masks_secret_values():
    bridge = Bridge()
    bridge.reset_bot()

    with activate_config_overrides({"bot_type": "openai", "open_ai_api_key": "sk-very-secret"}):
        cache_key = bridge._runtime_bot_cache_key("chat")

    assert "sk-very-secret" not in repr(cache_key)
    assert "sha256" in repr(cache_key)


def test_runtime_bot_cache_is_bounded(monkeypatch):
    import bridge.bridge as bridge_module

    bridge = Bridge()
    bridge.reset_bot()
    monkeypatch.setattr(bridge_module, "create_bot", lambda bot_type: {"bot_type": bot_type})

    for index in range(70):
        with activate_config_overrides({"bot_type": "openai", "open_ai_api_key": f"sk-{index}"}):
            bridge.get_bot("chat")

    assert len(bridge.bots) == 64
