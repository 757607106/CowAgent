"""
Session helpers shared by the platform-aware web handlers.

The project keeps session lifecycle operations in channel/web/handlers/workspace.py
because they need tenant/agent/binding scoping. Title generation is intentionally
local and deterministic so creating a new chat never triggers a second LLM call.
"""

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
    Generate a short session title without calling the model.

    The title endpoint runs after the assistant response. Calling the LLM here
    creates a visible post-answer delay and consumes an HTTP worker, so title
    generation uses the first meaningful user line instead. ``assistant_reply``
    is accepted to preserve the existing API contract.
    """
    del assistant_reply
    title = _truncate_fallback_title(user_message)
    logger.debug(f"[SessionService] Local title generation result: '{title}' (len={len(title)})")
    return title
