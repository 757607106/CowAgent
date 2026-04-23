"""
Cancellation support for the Agent execution pipeline.

Provides cooperative cancellation via threading.Event, allowing a new
message from the same session to interrupt an in-flight agent run.
"""

import threading
from typing import Dict, Optional


class CancelledError(Exception):
    """Raised when the current agent execution is cancelled by a newer request."""
    pass


class PreemptionError(Exception):
    """Raised when the current request is preempted by a newer request for the same session.

    This is a subclass of CancelledError that specifically indicates the cancellation
    was caused by a preemption (newer message arrived), not by an explicit cancel call.
    """
    pass


class CancelToken:
    """A cooperative cancellation token that can be passed through the execution chain.

    Wraps a threading.Event and provides a clean API for checking and triggering
    cancellation.
    """

    def __init__(self):
        self._event = threading.Event()

    def cancel(self):
        """Signal cancellation to all holders of this token."""
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._event.is_set()

    def check_cancelled(self):
        """Raise CancelledError if cancellation has been requested.

        Call this at cooperative yield points (before LLM calls, before tool
        execution, at the start of each agent turn).
        """
        if self._event.is_set():
            raise CancelledError("Agent execution cancelled by newer request")

    def wait(self, timeout: float = None) -> bool:
        """Block until cancelled or timeout expires.

        Returns True if cancelled, False if timeout expired.
        """
        return self._event.wait(timeout=timeout)


class CancelTokenRegistry:
    """Registry that maps session IDs to their active CancelTokens.

    Thread-safe: all operations are protected by an internal lock.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._tokens: Dict[str, CancelToken] = {}

    def get_or_create(self, session_id: str) -> CancelToken:
        """Get an existing CancelToken for the session, or create a new one."""
        with self._lock:
            if session_id not in self._tokens:
                self._tokens[session_id] = CancelToken()
            return self._tokens[session_id]

    def cancel_and_replace(self, session_id: str) -> CancelToken:
        """Cancel the existing token (if any) for the session and create a new one.

        This is the core preemption operation: when a new message arrives for
        a session, we cancel the old token and create a new one for the new
        request.

        Returns:
            The new CancelToken for the incoming request.
        """
        with self._lock:
            old_token = self._tokens.get(session_id)
            if old_token is not None and not old_token.is_cancelled:
                old_token.cancel()
                from common.log import logger
                logger.info(f"[CancelToken] Cancelled previous request for session={session_id}")
            new_token = CancelToken()
            self._tokens[session_id] = new_token
            return new_token

    def get(self, session_id: str) -> Optional[CancelToken]:
        """Get the current CancelToken for a session, or None."""
        with self._lock:
            return self._tokens.get(session_id)

    def remove(self, session_id: str):
        """Remove the CancelToken for a session (cleanup after execution completes)."""
        with self._lock:
            self._tokens.pop(session_id, None)

    def cancel_all(self):
        """Cancel all active tokens."""
        with self._lock:
            for token in self._tokens.values():
                if not token.is_cancelled:
                    token.cancel()

    @property
    def active_count(self) -> int:
        """Number of sessions with active (non-cancelled) tokens."""
        with self._lock:
            return sum(1 for t in self._tokens.values() if not t.is_cancelled)
