from __future__ import annotations

from agent.protocol.agent import Agent
from agent.protocol.agent_stream import AgentStreamExecutor
from agent.protocol.models import LLMModel
from agent.protocol.multimodal import (
    build_native_image_content,
    model_supports_native_image_input,
    sanitize_images_for_history,
)
from agent.tools.base_tool import BaseTool, ToolResult
from models.claudeapi.claude_api_bot import ClaudeAPIBot
from models.dashscope.dashscope_bot import DashscopeBot


class FakeAgent:
    memory_manager = None
    skill_manager = None
    last_usage = None

    def _get_model_context_window(self):
        return 100000

    def _estimate_message_tokens(self, message):
        return len(str(message))


class FakeNativeVisionModel(LLMModel):
    def __init__(self):
        super().__init__(model="qwen3.6-plus")
        self.last_request = None

    def call_stream(self, request):
        self.last_request = request
        yield {
            "choices": [
                {
                    "delta": {"content": '{"ok": true}'},
                    "finish_reason": "stop",
                }
            ]
        }


class VisionTool(BaseTool):
    name = "vision"
    description = "Analyze images"
    params = {"type": "object", "properties": {}}

    def __init__(self):
        self.image_builds = []

    def _build_image_content(self, image):
        self.image_builds.append(image)
        return {"type": "image_url", "image_url": {"url": "data:image/png;base64,tool"}}

    def execute(self, params):
        return ToolResult.success("should not run")


def test_model_support_detection_covers_native_vision_and_text_only_models():
    assert model_supports_native_image_input("qwen3.6-plus")
    assert model_supports_native_image_input("gpt-4o")
    assert model_supports_native_image_input("claude-sonnet-4-6")
    assert model_supports_native_image_input("gemini-3-flash-preview")
    assert model_supports_native_image_input("kimi-k2.6")
    assert model_supports_native_image_input("doubao-seed-2-0-pro-260215")
    assert model_supports_native_image_input("glm-4.5v")
    assert model_supports_native_image_input("MiniMax-Text-01")

    assert not model_supports_native_image_input("deepseek-chat")
    assert not model_supports_native_image_input("glm-4.7")
    assert not model_supports_native_image_input("MiniMax-M2.7")


def test_native_image_content_encodes_local_image_and_sanitizes_history(tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    content, refs = build_native_image_content(f"识别图片\n[图片: {image_path}]")

    assert refs == [str(image_path)]
    assert content is not None
    assert content[0]["type"] == "image_url"
    assert content[0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert content[1] == {"type": "text", "text": "识别图片"}

    sanitized = sanitize_images_for_history([{"role": "user", "content": content}])
    assert sanitized[0]["content"][0] == {"type": "text", "text": "[图片]"}


def test_native_image_content_reuses_existing_image_builder():
    calls = []

    def build_image_content(image):
        calls.append(image)
        return {"type": "image_url", "image_url": {"url": "data:image/png;base64,built"}}

    content, refs = build_native_image_content("识别\n[图片: file:///tmp/sample.png]", build_image_content)

    assert refs == ["file:///tmp/sample.png"]
    assert calls == ["/tmp/sample.png"]
    assert content[0]["image_url"]["url"] == "data:image/png;base64,built"


def test_native_multimodal_request_skips_vision_tool(tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    model = FakeNativeVisionModel()
    vision_tool = VisionTool()
    executor = AgentStreamExecutor(
        agent=FakeAgent(),
        model=model,
        system_prompt="",
        tools=[vision_tool],
        max_turns=3,
    )

    response = executor.run_stream(f"图片转 JSON\n[图片: {image_path}]")

    assert response == '{"ok": true}'
    assert vision_tool.image_builds == [str(image_path)]
    assert model.last_request is not None
    assert not model.last_request.tools
    user_content = next(
        msg["content"]
        for msg in model.last_request.messages
        if msg.get("role") == "user"
    )
    assert user_content[0]["type"] == "image_url"
    assert user_content[0]["image_url"]["url"] == "data:image/png;base64,tool"
    assert user_content[1]["text"] == "图片转 JSON"


def test_agent_prompt_and_schema_hide_vision_for_native_multimodal_run(tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    model = FakeNativeVisionModel()
    vision_tool = VisionTool()
    agent = Agent(
        system_prompt="",
        model=model,
        tools=[vision_tool],
        output_mode="logger",
        enable_skills=False,
        knowledge_enabled=False,
    )

    response = agent.run_stream(f"图片转 JSON\n[图片: {image_path}]", clear_history=True)

    assert response == '{"ok": true}'
    assert model.last_request is not None
    assert not model.last_request.tools
    assert "vision" not in (model.last_request.system or "").lower()
    assert vision_tool.image_builds == [str(image_path)]


def test_dashscope_multimodal_conversion_accepts_openai_image_blocks():
    converted = DashscopeBot._prepare_messages_for_multimodal([
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
                {"type": "text", "text": "提取内容"},
            ],
        }
    ])

    assert converted[0]["content"] == [
        {"image": "data:image/png;base64,abc"},
        {"text": "提取内容"},
    ]


def test_dashscope_routes_qwen_vision_models_to_multimodal_api():
    assert DashscopeBot._is_multimodal_model("qwen3.6-plus")
    assert DashscopeBot._is_multimodal_model("qwen-vl-max")
    assert DashscopeBot._is_multimodal_model("qvq-max")


def test_claude_sanitize_converts_openai_image_block_to_native_image():
    converted = ClaudeAPIBot._sanitize_message({
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
            {"type": "text", "text": "Describe it"},
        ],
    })

    assert converted["content"][0] == {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": "abc"},
    }
    assert converted["content"][1] == {"type": "text", "text": "Describe it"}
