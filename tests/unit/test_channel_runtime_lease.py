from types import SimpleNamespace
from unittest.mock import Mock

import pytest


class FakeChannelConfigService:
    def build_runtime_overrides(self, definition):
        return {"feishu_event_mode": "websocket"}


class FakeLeaseService:
    ttl_seconds = 90

    def __init__(self, acquired=True):
        self.acquired = acquired
        self.acquire_calls = []
        self.release_calls = []

    def acquire(self, definition):
        self.acquire_calls.append(definition.channel_config_id)
        return SimpleNamespace(acquired=self.acquired, lease_until="2099-01-01T00:00:00Z")

    def heartbeat(self, channel_config_id):
        return True

    def release(self, channel_config_id):
        self.release_calls.append(channel_config_id)
        return True


def _definition():
    return SimpleNamespace(
        tenant_id="tenant-a",
        channel_config_id="cfg-a",
        channel_type="feishu",
    )


def test_channel_manager_skips_runtime_when_lease_is_owned_elsewhere(monkeypatch):
    import app
    import cow_platform.runtime.channel_manager as channel_manager_module
    import cow_platform.services.channel_config_service as channel_config_module

    monkeypatch.setattr(channel_config_module, "ChannelConfigService", FakeChannelConfigService)
    monkeypatch.setattr(channel_manager_module, "_clear_singleton_cache", lambda channel_type: None)
    create_channel = Mock(side_effect=AssertionError("channel must not start without lease"))
    monkeypatch.setattr(channel_manager_module.channel_factory, "create_channel", create_channel)

    manager = app.ChannelManager()
    manager._runtime_leases = FakeLeaseService(acquired=False)

    manager.start_channel_config(_definition())

    assert manager._runtime_leases.acquire_calls == ["cfg-a"]
    create_channel.assert_not_called()
    assert manager.get_channel_config("cfg-a") is None


def test_channel_manager_releases_lease_when_runtime_creation_fails(monkeypatch):
    import app
    import cow_platform.runtime.channel_manager as channel_manager_module
    import cow_platform.services.channel_config_service as channel_config_module

    monkeypatch.setattr(channel_config_module, "ChannelConfigService", FakeChannelConfigService)
    monkeypatch.setattr(channel_manager_module, "_clear_singleton_cache", lambda channel_type: None)
    monkeypatch.setattr(channel_manager_module.channel_factory, "create_channel", Mock(side_effect=RuntimeError("boom")))

    manager = app.ChannelManager()
    lease_service = FakeLeaseService(acquired=True)
    manager._runtime_leases = lease_service

    with pytest.raises(RuntimeError):
        manager.start_channel_config(_definition())

    assert lease_service.acquire_calls == ["cfg-a"]
    assert lease_service.release_calls == ["cfg-a"]
    assert manager.get_channel_config("cfg-a") is None


def test_channel_manager_sync_stops_stale_channel_config():
    import app

    manager = app.ChannelManager()
    lease_service = FakeLeaseService(acquired=True)
    manager._runtime_leases = lease_service
    manager._channels["cfg-a"] = SimpleNamespace(channel_config_id="cfg-a", stop=lambda: None)
    manager._threads["cfg-a"] = None

    manager.sync_channel_configs([])

    assert manager.get_channel_config("cfg-a") is None
    assert lease_service.release_calls == ["cfg-a"]
