from agent.memory import conversation_persistence
from agent.memory.conversation_store import _group_into_display_turns


def test_persist_messages_honors_config_switch(monkeypatch) -> None:
    called = []
    import config as config_module

    monkeypatch.setattr(config_module, "conf", lambda: {"conversation_persistence": False})

    def fail_store():
        called.append(True)
        raise AssertionError("store should not be touched")

    import agent.memory

    monkeypatch.setattr(agent.memory, "get_conversation_store", fail_store)

    conversation_persistence.persist_messages("s1", [{"role": "user", "content": "hi"}], source="Test")

    assert called == []


def test_clear_session_if_empty_only_clears_empty_sessions(monkeypatch) -> None:
    cleared = []

    class Store:
        def clear_session(self, session_id):
            cleared.append(session_id)

    import agent.memory

    monkeypatch.setattr(agent.memory, "get_conversation_store", lambda: Store())

    conversation_persistence.clear_session_if_empty("non-empty", 1, source="Test")
    conversation_persistence.clear_session_if_empty("empty", 0, source="Test")

    assert cleared == ["empty"]


def test_history_replays_thinking_when_message_metadata_enabled() -> None:
    rows = [
        ("user", [{"type": "text", "text": "问题"}], 1, {}),
        (
            "assistant",
            [
                {"type": "thinking", "thinking": "先分析"},
                {"type": "text", "text": "答案"},
            ],
            2,
            {"enable_thinking": True},
        ),
    ]

    messages = _group_into_display_turns(rows, include_thinking=False)

    assert messages[1]["steps"] == [
        {"type": "thinking", "content": "先分析"},
        {"type": "content", "content": "答案"},
    ]


def test_history_hides_thinking_when_message_metadata_disabled() -> None:
    rows = [
        ("user", [{"type": "text", "text": "问题"}], 1, {}),
        (
            "assistant",
            [
                {"type": "thinking", "thinking": "不应回放"},
                {"type": "text", "text": "答案"},
            ],
            2,
            {"enable_thinking": False},
        ),
    ]

    messages = _group_into_display_turns(rows, include_thinking=True)

    assert messages[1]["steps"] == [{"type": "content", "content": "答案"}]
