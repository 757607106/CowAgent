from bridge.context import Context, ContextType
from bridge.reply import Reply, ReplyType
from channel.channel import Channel
from config import conf


class _FailingAgentBridge:
    def __init__(self):
        self.fallback_called = False

    def fetch_agent_reply(self, **kwargs):
        raise RuntimeError("agent failed")

    def fetch_reply_content(self, query, context):
        self.fallback_called = True
        return Reply(ReplyType.TEXT, "fallback")


def test_platform_agent_failure_does_not_fallback_to_plain_chat(monkeypatch):
    import channel.channel as channel_module

    fake_bridge = _FailingAgentBridge()
    monkeypatch.setattr(channel_module, "Bridge", lambda: fake_bridge)
    monkeypatch.setitem(conf(), "agent", True)
    monkeypatch.setitem(conf(), "web_tenant_auth", True)

    reply = Channel().build_reply_content("hello", Context(ContextType.TEXT, "hello"))

    assert reply.type == ReplyType.ERROR
    assert fake_bridge.fallback_called is False


def test_legacy_agent_failure_keeps_existing_plain_chat_fallback(monkeypatch):
    import channel.channel as channel_module

    fake_bridge = _FailingAgentBridge()
    monkeypatch.setattr(channel_module, "Bridge", lambda: fake_bridge)
    monkeypatch.setitem(conf(), "agent", True)
    monkeypatch.setitem(conf(), "web_tenant_auth", False)

    reply = Channel().build_reply_content("hello", Context(ContextType.TEXT, "hello"))

    assert reply.type == ReplyType.TEXT
    assert reply.content == "fallback"
    assert fake_bridge.fallback_called is True
