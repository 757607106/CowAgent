from __future__ import annotations

from common.log import logger


def persist_messages(session_id: str, new_messages: list, channel_type: str = "", *, source: str = "Agent") -> None:
    if not new_messages:
        return
    try:
        from config import conf

        if not conf().get("conversation_persistence", True):
            return
    except Exception:
        pass
    try:
        from agent.memory import get_conversation_store

        get_conversation_store().append_messages(
            session_id,
            new_messages,
            channel_type=channel_type,
        )
    except Exception as e:
        logger.warning(f"[{source}] Failed to persist messages for session={session_id}: {e}")


def clear_session_if_empty(session_id: str, message_count: int, *, source: str = "Agent") -> None:
    if message_count != 0:
        return
    try:
        from agent.memory import get_conversation_store

        get_conversation_store().clear_session(session_id)
        logger.info(f"[{source}] Cleared DB for session: {session_id}")
    except Exception as e:
        logger.warning(f"[{source}] Failed to clear DB after recovery: {e}")
