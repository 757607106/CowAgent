from bridge.agent_initializer import AgentInitializer
from bridge.context import Context, ContextType
from bridge.reply import Reply, ReplyType
from channel.chat_channel import ChatChannel
from config import _parse_env_value
from cow_platform.runtime.scope import activate_config_overrides


def test_parse_env_value_does_not_eval_python_code(tmp_path):
    marker = tmp_path / "executed"
    payload = f"__import__('pathlib').Path({str(marker)!r}).touch()"

    assert _parse_env_value(payload) == payload
    assert not marker.exists()


def test_embedding_config_skips_endpoint_specific_openai_base():
    model, api_key, api_base = AgentInitializer._resolve_embedding_api_config(
        {
            "embedding_model": "",
            "embedding_api_key": "",
            "embedding_api_base": "",
            "open_ai_api_key": "sk-chat",
            "open_ai_api_base": "https://api.example.test/v4/images/generations",
        }
    )

    assert model == "text-embedding-3-small"
    assert api_key == ""
    assert api_base == ""


def test_embedding_config_prefers_explicit_embedding_base():
    model, api_key, api_base = AgentInitializer._resolve_embedding_api_config(
        {
            "embedding_model": "embed-model",
            "embedding_api_key": "sk-embedding",
            "embedding_api_base": "https://embed.example.test/v1",
            "open_ai_api_key": "sk-chat",
            "open_ai_api_base": "https://api.example.test/v4/images/generations",
        }
    )

    assert model == "embed-model"
    assert api_key == "sk-embedding"
    assert api_base == "https://embed.example.test/v1"


def test_image_generation_uses_bridge_under_runtime_overrides(monkeypatch):
    import channel.chat_channel as chat_channel_module

    captured = {}

    class _Bridge:
        def fetch_reply_content(self, query, context):
            from config import conf

            captured["query"] = query
            captured["context_type"] = context.type
            captured["bot_type"] = conf().get("bot_type")
            captured["text_to_image"] = conf().get("text_to_image")
            captured["api_key"] = conf().get("open_ai_api_key")
            return Reply(ReplyType.IMAGE_URL, "https://image.example.test/out.png")

    monkeypatch.setattr(chat_channel_module, "Bridge", lambda: _Bridge())
    channel = object.__new__(ChatChannel)
    context = Context(ContextType.IMAGE_CREATE, "画一张图", kwargs={"session_id": "s1"})

    with activate_config_overrides(
        {
            "bot_type": "openai",
            "text_to_image": "tenant-image-model",
            "open_ai_api_key": "sk-image",
        }
    ):
        reply = channel._build_capability_image_reply(context, object())

    assert reply.type == ReplyType.IMAGE_URL
    assert captured == {
        "query": "画一张图",
        "context_type": ContextType.IMAGE_CREATE,
        "bot_type": "openai",
        "text_to_image": "tenant-image-model",
        "api_key": "sk-image",
    }


def test_vision_model_uses_tools_namespace():
    from agent.tools.vision.vision import Vision

    vision = object.__new__(Vision)
    with activate_config_overrides(
        {
            "model": "gpt-4o-mini",
            "tools": {"vision": {"model": "current-vision"}},
        }
    ):
        assert vision._resolve_vision_model() == "current-vision"
