from agent.protocol.agent_stream import AgentStreamExecutor
from agent.protocol.models import LLMModel
from agent.tools.base_tool import BaseTool, ToolResult


class FakeModel(LLMModel):
    def __init__(self):
        super().__init__(model="fake-model")
        self.calls = 0

    def call_stream(self, request):
        self.calls += 1
        if self.calls == 1:
            chunks = [
                "<tool",
                "_call>\n<function=memory_search>\n",
                "<parameter=query>\ndeep agent\n</parameter>\n",
                "</function>\n</tool_call>",
            ]
            for chunk in chunks:
                yield {
                    "choices": [
                        {
                            "delta": {"content": chunk},
                            "finish_reason": None,
                        }
                    ]
                }
            yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}
            return

        yield {
            "choices": [
                {
                    "delta": {"content": "Deep Agent 是一种面向复杂任务的智能体模式。"},
                    "finish_reason": "stop",
                }
            ]
        }


class FakeAgent:
    memory_manager = None
    skill_manager = None
    last_usage = None

    def _get_model_context_window(self):
        return 100000

    def _estimate_message_tokens(self, message):
        return len(str(message))


class MemorySearchTool(BaseTool):
    name = "memory_search"
    description = "Search memory"
    params = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }

    def __init__(self):
        self.calls = []

    def execute(self, params):
        self.calls.append(params)
        return ToolResult.success("Deep Agent related memory")


def test_text_tool_call_is_executed_and_not_streamed_as_answer():
    events = []
    model = FakeModel()
    tool = MemorySearchTool()
    executor = AgentStreamExecutor(
        agent=FakeAgent(),
        model=model,
        system_prompt="",
        tools=[tool],
        max_turns=3,
        on_event=events.append,
    )

    response = executor.run_stream("你知道 deep agent 吗")

    assert response == "Deep Agent 是一种面向复杂任务的智能体模式。"
    assert tool.calls == [{"query": "deep agent"}]
    assert model.calls == 2

    streamed_text = "".join(
        event.get("data", {}).get("delta", "")
        for event in events
        if event.get("type") == "message_update"
    )
    assert "<tool_call>" not in streamed_text
    assert any(event.get("type") == "tool_execution_start" for event in events)
    assert any(event.get("type") == "tool_execution_end" for event in events)
