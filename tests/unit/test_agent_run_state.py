import threading

from agent.protocol.run_state import sync_executor_messages


class _Agent:
    def __init__(self):
        self.messages = []
        self.messages_lock = threading.Lock()


def test_sync_executor_messages_returns_new_tail_without_trim():
    agent = _Agent()
    agent.messages = [{"role": "user", "content": "old"}]
    executor_messages = [
        {"role": "user", "content": "old"},
        {"role": "user", "content": "new"},
        {"role": "assistant", "content": "answer"},
    ]

    new_messages = sync_executor_messages(agent, executor_messages, original_length=1)

    assert new_messages == executor_messages[1:]
    assert agent.messages == executor_messages


def test_sync_executor_messages_handles_trim_and_sanitizes_images():
    agent = _Agent()
    agent.messages = [{"role": "user", "content": f"old-{idx}"} for idx in range(5)]
    executor_messages = [
        {"role": "assistant", "content": "kept summary"},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,secret"}},
                {"type": "text", "text": "new"},
            ],
        },
        {"role": "assistant", "content": "answer"},
    ]

    new_messages = sync_executor_messages(agent, executor_messages, original_length=5)

    assert new_messages == agent.messages[1:]
    assert agent.messages[1]["content"][0] == {"type": "text", "text": "[图片]"}
