import os

import app
from bridge.agent_initializer import AgentInitializer
import bridge.agent_initializer as agent_initializer_module
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


def test_app_imports_local_platform_env(monkeypatch, tmp_path):
    for key in (
        "AGENT_WORKSPACE",
        "COW_PLATFORM_DATABASE_URL",
        "COW_PLATFORM_REDIS_URL",
        "COW_PLATFORM_QDRANT_URL",
        "COW_PLATFORM_MINIO_ENDPOINT",
        "MODEL",
        "PLATFORM_POSTGRES_PASSWORD",
        "WEB_PORT",
        "WEB_TENANT_AUTH",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HOME", "/tmp/cow-home")

    (tmp_path / ".env.platform").write_text(
        "\n".join(
            [
                "PLATFORM_POSTGRES_USER=cowplatform",
                "PLATFORM_POSTGRES_PASSWORD=prod-smoke-db-secret",
                "PLATFORM_POSTGRES_DB=cowplatform",
                "PLATFORM_POSTGRES_PORT=55432",
                "PLATFORM_REDIS_PORT=56379",
                "PLATFORM_QDRANT_HTTP_PORT=56333",
                "PLATFORM_MINIO_API_PORT=59000",
                "PLATFORM_MINIO_ROOT_USER=cowplatform-prod",
                "PLATFORM_MINIO_ROOT_PASSWORD=prod-smoke-minio-secret",
                "PLATFORM_MINIO_BUCKET=coreagent",
                "WEB_PORT=9899",
                "MODEL=qwen3.6-plus",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / ".env.local").write_text(
        "\n".join(
            [
                'if [ -f ".env.platform" ]; then',
                '  source ".env.platform"',
                "fi",
                "LOCAL_WEB_PORT=9901",
                "COW_PLATFORM_DATABASE_URL=postgresql://${PLATFORM_POSTGRES_USER:-cowplatform}:${PLATFORM_POSTGRES_PASSWORD:-prod-smoke-db-secret}@127.0.0.1:${PLATFORM_POSTGRES_PORT:-55432}/${PLATFORM_POSTGRES_DB:-cowplatform}",
                "COW_PLATFORM_REDIS_URL=redis://127.0.0.1:${PLATFORM_REDIS_PORT:-56379}/0",
                "COW_PLATFORM_QDRANT_URL=http://127.0.0.1:${PLATFORM_QDRANT_HTTP_PORT:-56333}",
                "COW_PLATFORM_MINIO_ENDPOINT=http://127.0.0.1:${PLATFORM_MINIO_API_PORT:-59000}",
                "COW_PLATFORM_MINIO_ACCESS_KEY=${PLATFORM_MINIO_ROOT_USER:-cowplatform-prod}",
                "COW_PLATFORM_MINIO_SECRET_KEY=${PLATFORM_MINIO_ROOT_PASSWORD:-prod-smoke-minio-secret}",
                "COW_PLATFORM_MINIO_BUCKET=${PLATFORM_MINIO_BUCKET:-coreagent}",
                "WEB_TENANT_AUTH=true",
                "WEB_PORT=${LOCAL_WEB_PORT}",
                "MODEL=${MODEL:-qwen3.6-plus}",
                "AGENT_WORKSPACE=${AGENT_WORKSPACE:-$HOME/cow}",
            ]
        ),
        encoding="utf-8",
    )

    app._import_local_platform_env(tmp_path)

    assert os.environ["WEB_PORT"] == "9901"
    assert os.environ["MODEL"] == "qwen3.6-plus"
    assert os.environ["WEB_TENANT_AUTH"] == "true"
    assert os.environ["AGENT_WORKSPACE"] == "/tmp/cow-home/cow"
    assert os.environ["COW_PLATFORM_DATABASE_URL"] == (
        "postgresql://cowplatform:prod-smoke-db-secret@127.0.0.1:55432/cowplatform"
    )
    assert os.environ["COW_PLATFORM_REDIS_URL"] == "redis://127.0.0.1:56379/0"
    assert os.environ["COW_PLATFORM_QDRANT_URL"] == "http://127.0.0.1:56333"
    assert os.environ["COW_PLATFORM_MINIO_ENDPOINT"] == "http://127.0.0.1:59000"


def test_app_local_platform_env_can_be_disabled(monkeypatch, tmp_path):
    monkeypatch.delenv("WEB_PORT", raising=False)
    monkeypatch.setenv("COW_PLATFORM_AUTO_LOCAL_ENV", "false")
    (tmp_path / ".env.local").write_text("WEB_PORT=9901\n", encoding="utf-8")

    app._import_local_platform_env(tmp_path)

    assert "WEB_PORT" not in os.environ


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


def test_platform_initializer_skips_global_agent_env(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_BASE=https://open.bigmodel.cn/api/paas/v4/images/generations\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_BASE", "https://runtime.example.test/v1")
    monkeypatch.setattr(agent_initializer_module, "expand_path", lambda path: str(env_file))

    initializer = object.__new__(AgentInitializer)
    with activate_config_overrides({"web_tenant_auth": True}):
        initializer._load_env_file()

    assert os.environ["OPENAI_API_BASE"] == "https://runtime.example.test/v1"


def test_memory_manager_can_disable_host_env_embedding(monkeypatch, tmp_path):
    import agent.memory.manager as memory_manager_module
    from agent.memory import MemoryConfig, MemoryManager

    monkeypatch.setenv("OPENAI_API_KEY", "host-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://api.example.test/v4/images/generations")

    calls = []

    def fake_create_embedding_provider(**kwargs):
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(memory_manager_module, "create_embedding_provider", fake_create_embedding_provider)

    manager = MemoryManager(
        MemoryConfig(workspace_root=str(tmp_path)),
        allow_env_embedding=False,
    )

    assert manager.embedding_provider is None
    assert calls == []


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
