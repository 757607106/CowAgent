from agent.chat import session_service


def test_generate_session_title_uses_first_meaningful_line_without_model_call(monkeypatch) -> None:
    def fail_if_model_is_loaded(*_args, **_kwargs):
        raise AssertionError("title generation must not load the chat model")

    monkeypatch.setattr("builtins.__import__", fail_if_model_is_loaded)

    title = session_service.generate_session_title(
        "\n  测试标题生成是否快速  \n第二行不用",
        "这段助手回复不应该触发模型调用",
    )

    assert title == "测试标题生成是否快速"


def test_generate_session_title_truncates_long_input() -> None:
    title = session_service.generate_session_title("这是一段非常长的用户消息，需要被截断避免会话列表标题过长影响展示")

    assert title == "这是一段非常长的用户消息，需要被截断避免会话列表标题过长影响..."


def test_generate_session_title_uses_new_chat_for_empty_input() -> None:
    assert session_service.generate_session_title("\n \t") == "New Chat"
