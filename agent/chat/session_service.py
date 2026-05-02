"""
Session helpers shared by the platform-aware web handlers.

The project keeps session lifecycle operations in channel/web/handlers/workspace.py
because they need tenant/agent/binding scoping. Title generation is shared here
so web code and future non-web callers do not duplicate the LLM fallback logic.
"""

import re

from common.log import logger


def _truncate_fallback_title(user_message: str, max_len: int = 30) -> str:
    """Pick the first non-empty line of the user message and truncate it."""
    if not user_message:
        return "New Chat"
    first_line = ""
    for line in user_message.splitlines():
        line = line.strip()
        if line:
            first_line = line
            break
    if not first_line:
        return "New Chat"
    if len(first_line) > max_len:
        first_line = first_line[:max_len].rstrip() + "..."
    return first_line


def generate_session_title(user_message: str, assistant_reply: str = "") -> str:
    """
    Generate a short session title by calling the current bot.

    Falls back to the first meaningful line of the user message when the model
    call fails or returns a zero-token error sentinel.
    """
    fallback = _truncate_fallback_title(user_message)
    try:
        from bridge.bridge import Bridge
        from models.session_manager import Session

        bot = Bridge().get_bot("chat")
        prompt_parts = [f"User: {user_message[:300]}"]
        if assistant_reply:
            prompt_parts.append(f"Assistant: {assistant_reply[:300]}")

        session = Session("__title_gen__", system_prompt="")
        session.messages = [
            {
                "role": "user",
                "content": (
                    "Generate a very short title (max 15 characters for Chinese, max 6 words for English) "
                    "summarizing this conversation. Return ONLY the title text, nothing else.\n\n"
                    + "\n".join(prompt_parts)
                ),
            }
        ]

        result = bot.reply_text(session) or {}
        completion_tokens = result.get("completion_tokens", 0) or 0
        raw = (result.get("content") or "").strip()
        if completion_tokens <= 0:
            logger.warning(
                "[SessionService] Title generation got empty completion "
                f"(completion_tokens={completion_tokens}, content='{raw[:50]}'), using fallback"
            )
            return fallback

        title = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip().strip('"\'')
        logger.info(f"[SessionService] Title generation result: '{title}' (len={len(title)})")
        if title and len(title) <= 50:
            return title
    except Exception as e:
        logger.warning(f"[SessionService] Title generation failed: {e}")
    return fallback
