from plugins.event import Event, EventContext
from plugins.plugin_manager import PluginManager


class PlatformConfig:
    def get(self, key, default=None):
        if key == "web_tenant_auth":
            return True
        return default


def test_platform_mode_load_plugins_is_noop(monkeypatch):
    import plugins.plugin_manager as plugin_manager_module

    manager = PluginManager(_singleton_key="platform-noop-load")
    manager.plugins["OLD"] = type("OldPlugin", (), {"priority": 1})
    manager.instances["OLD"] = object()
    manager.listening_plugins[Event.ON_RECEIVE_MESSAGE] = ["OLD"]

    monkeypatch.setattr(plugin_manager_module, "conf", lambda: PlatformConfig())
    monkeypatch.setattr(manager, "load_config", lambda: (_ for _ in ()).throw(AssertionError("must not read plugins.json")))
    monkeypatch.setattr(manager, "scan_plugins", lambda: (_ for _ in ()).throw(AssertionError("must not scan plugins")))

    manager.load_plugins()

    assert list(manager.plugins.keys()) == []
    assert manager.instances == {}
    assert manager.listening_plugins == {}


def test_platform_mode_emit_event_passes_through(monkeypatch):
    import plugins.plugin_manager as plugin_manager_module

    manager = PluginManager(_singleton_key="platform-noop-emit")
    called = {"value": False}

    class FakePlugin:
        enabled = True
        priority = 1

    def handler(_context):
        called["value"] = True

    manager.plugins["FAKE"] = FakePlugin
    manager.instances["FAKE"] = type("FakeInstance", (), {"handlers": {Event.ON_RECEIVE_MESSAGE: handler}})()
    manager.listening_plugins[Event.ON_RECEIVE_MESSAGE] = ["FAKE"]
    monkeypatch.setattr(plugin_manager_module, "conf", lambda: PlatformConfig())

    event_context = EventContext(Event.ON_RECEIVE_MESSAGE, {"context": object()})
    returned = manager.emit_event(event_context)

    assert returned is event_context
    assert called["value"] is False


def test_platform_mode_plugin_mutations_are_rejected(monkeypatch):
    import plugins.plugin_manager as plugin_manager_module

    manager = PluginManager(_singleton_key="platform-noop-mutate")
    monkeypatch.setattr(plugin_manager_module, "conf", lambda: PlatformConfig())

    assert manager.enable_plugin("godcmd")[0] is False
    assert manager.install_plugin("https://example.com/plugin.git")[0] is False
    assert manager.update_plugin("anything")[0] is False
    assert manager.uninstall_plugin("anything")[0] is False
