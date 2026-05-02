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


def test_image_generation_skill_uses_runtime_overrides(monkeypatch, tmp_path):
    import json
    from types import SimpleNamespace

    import cow_platform.services.image_generation_service as image_service_module

    captured = {}

    class _Completed:
        returncode = 0
        stdout = json.dumps({"images": [{"url": str(tmp_path / "out.png")}], "model": "tenant-image-model"})
        stderr = ""

    def fake_run(cmd, cwd, env, text, stdout, stderr, timeout):
        captured["cmd"] = cmd
        captured["env"] = env
        captured["timeout"] = timeout
        return _Completed()

    monkeypatch.setattr(image_service_module.subprocess, "run", fake_run)
    channel = object.__new__(ChatChannel)
    context = Context(ContextType.IMAGE_CREATE, "画一张图", kwargs={"session_id": "s1", "request_id": "req-1"})

    with activate_config_overrides(
        {
            "open_ai_api_key": "sk-image",
            "open_ai_api_base": "https://image.example.test/v1",
            "skill": {"image-generation": {"model": "tenant-image-model"}},
        }
    ):
        reply = channel._build_capability_image_reply(context, SimpleNamespace(metadata={}))

    assert reply.type == ReplyType.TEXT
    assert "generated_images" in captured["env"]["IMAGE_OUTPUT_DIR"]
    assert captured["env"]["OPENAI_API_KEY"] == "sk-image"
    assert captured["env"]["OPENAI_API_BASE"] == "https://image.example.test/v1"
    assert captured["env"]["SKILL_IMAGE_GENERATION_MODEL"] == "tenant-image-model"
    assert captured["timeout"] == 600
    assert "api/file?path=" in reply.content


def test_runtime_environment_merges_scope_over_host_env(monkeypatch):
    from cow_platform.runtime.environment import build_runtime_environment

    monkeypatch.setenv("OPENAI_API_KEY", "host-key")

    with activate_config_overrides(
        {
            "open_ai_api_key": "runtime-key",
            "skill": {"image-generation": {"model": "runtime-image-model"}},
        }
    ):
        env = build_runtime_environment(extra_env={"IMAGE_OUTPUT_DIR": "/tmp/images"})

    assert env["OPENAI_API_KEY"] == "runtime-key"
    assert env["SKILL_IMAGE_GENERATION_MODEL"] == "runtime-image-model"
    assert env["IMAGE_OUTPUT_DIR"] == "/tmp/images"


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


def test_vision_capability_service_resolves_runtime_provider(monkeypatch):
    from types import SimpleNamespace

    import cow_platform.services.vision_capability_service as vision_capability_module
    from cow_platform.services.vision_capability_service import VisionCapabilityService

    class FakeCapabilityService:
        def resolve_for_runtime(self, tenant_id, capability):
            assert tenant_id == "tenant-a"
            assert capability == "multimodal"
            return SimpleNamespace(
                capability_config_id="cap-mm",
                provider="openai",
                display_name="Tenant Vision",
                model_name="gpt-4o-mini",
                api_key="sk-vision",
                api_base="https://vision.example.test/v1",
            )

        def build_runtime_overrides(self, definition):
            return {
                "open_ai_api_key": definition.api_key,
                "tools": {
                    "vision": {
                        "model": definition.model_name,
                        "provider": definition.provider,
                    },
                },
            }

    monkeypatch.setattr(
        vision_capability_module,
        "get_current_runtime_context",
        lambda: SimpleNamespace(tenant_id="tenant-a"),
    )
    monkeypatch.setattr(
        vision_capability_module,
        "get_current_config_overrides",
        lambda: {"model": "tenant-chat-model"},
    )

    provider = VisionCapabilityService(capability_service=FakeCapabilityService()).resolve_provider()

    assert provider is not None
    assert provider.name == "Tenant Vision"
    assert provider.provider == "openai"
    assert provider.api_key == "sk-vision"
    assert provider.model_name == "gpt-4o-mini"
    assert provider.config_overrides["model"] == "tenant-chat-model"
    assert provider.config_overrides["tools"]["vision"]["model"] == "gpt-4o-mini"
