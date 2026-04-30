from __future__ import annotations

from typing import Any

from agent.protocol.multimodal import sanitize_images_for_history


def sync_executor_messages(agent: Any, executor_messages: list[dict[str, Any]], original_length: int) -> list[dict[str, Any]]:
    """Replace agent history with executor history and return messages added in the current run."""
    sanitized_messages = sanitize_images_for_history(list(executor_messages))
    with agent.messages_lock:
        if len(sanitized_messages) < original_length:
            new_start = _find_current_user_turn_start(sanitized_messages, original_length)
            new_messages = list(sanitized_messages[new_start:])
        else:
            new_messages = list(sanitized_messages[original_length:])
        agent.messages = sanitized_messages
    return new_messages


def _find_current_user_turn_start(messages: list[dict[str, Any]], fallback: int) -> int:
    for idx in range(len(messages) - 1, -1, -1):
        if _is_plain_user_query(messages[idx]):
            return idx
    return min(fallback, len(messages))


def _is_plain_user_query(message: dict[str, Any]) -> bool:
    if message.get("role") != "user":
        return False
    content = message.get("content", [])
    if isinstance(content, str):
        return True
    if not isinstance(content, list):
        return False
    has_text = any(isinstance(block, dict) and block.get("type") == "text" for block in content)
    has_tool_result = any(isinstance(block, dict) and block.get("type") == "tool_result" for block in content)
    return has_text and not has_tool_result
