from bridge.agent_event_handler import AgentEventHandler


def test_agent_event_handler_collects_tool_and_mcp_usage_metrics() -> None:
    handler = AgentEventHandler()

    handler.handle_event(
        {
            "type": "tool_execution_start",
            "data": {"tool_call_id": "call-1", "tool_name": "read", "arguments": {"path": "README.md"}},
        }
    )
    handler.handle_event(
        {
            "type": "tool_execution_end",
            "data": {"tool_call_id": "call-1", "tool_name": "read", "status": "success", "execution_time": 0.25},
        }
    )
    handler.handle_event(
        {
            "type": "tool_execution_end",
            "data": {
                "tool_call_id": "call-2",
                "tool_name": "mcp_docs_search",
                "status": "error",
                "execution_time": 0.5,
            },
        }
    )

    metrics = handler.get_usage_metrics()

    assert metrics["tool_call_count"] == 2
    assert metrics["mcp_call_count"] == 1
    assert metrics["tool_error_count"] == 1
    assert metrics["tool_execution_time_ms"] == 750
    assert metrics["tool_names"] == {"read": 1, "mcp_docs_search": 1}
