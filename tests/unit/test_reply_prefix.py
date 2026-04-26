from bridge.context import Context, ContextType
from bridge.reply import Reply, ReplyType
from channel import chat_channel
from channel.chat_channel import ChatChannel
from config import available_setting, conf


class FakePluginManager:
    def emit_event(self, event_context):
        return event_context


def test_platform_default_reply_prefix_is_empty() -> None:
    assert available_setting["single_chat_reply_prefix"] == ""


def test_private_text_reply_has_no_legacy_bot_prefix(monkeypatch) -> None:
    monkeypatch.setattr(chat_channel, "PluginManager", lambda: FakePluginManager())
    monkeypatch.setitem(conf(), "single_chat_reply_prefix", "")
    monkeypatch.setitem(conf(), "single_chat_reply_suffix", "")

    channel = ChatChannel.__new__(ChatChannel)
    context = Context(ContextType.TEXT, "hello", kwargs={"isgroup": False})
    reply = Reply(ReplyType.TEXT, "你好")

    decorated = channel._decorate_reply(context, reply)

    assert decorated.content == "你好"
