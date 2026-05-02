from agent.memory import conversation_persistence


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
