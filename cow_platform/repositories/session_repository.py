from __future__ import annotations

from typing import Any

from agent.memory.conversation_store import ConversationStore

from cow_platform.repositories.agent_repository import AgentRepository


class SessionRepository:
    """按 Agent 工作区隔离的会话仓储。"""

    def __init__(self, agent_repository: AgentRepository | None = None):
        self.agent_repository = agent_repository or AgentRepository()

    def list_sessions(
        self,
        tenant_id: str,
        agent_id: str,
        *,
        channel_type: str = "",
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        store = self._get_store(tenant_id, agent_id)
        return store.list_sessions(channel_type=channel_type, page=page, page_size=page_size)

    def load_history_page(
        self,
        tenant_id: str,
        agent_id: str,
        session_id: str,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        store = self._get_store(tenant_id, agent_id)
        return store.load_history_page(session_id=session_id, page=page, page_size=page_size)

    def clear_session(self, tenant_id: str, agent_id: str, session_id: str) -> None:
        store = self._get_store(tenant_id, agent_id)
        store.clear_session(session_id)

    def rename_session(self, tenant_id: str, agent_id: str, session_id: str, title: str) -> bool:
        store = self._get_store(tenant_id, agent_id)
        return store.rename_session(session_id, title)

    def clear_context(self, tenant_id: str, agent_id: str, session_id: str) -> int:
        store = self._get_store(tenant_id, agent_id)
        return store.clear_context(session_id)

    def append_messages(
        self,
        tenant_id: str,
        agent_id: str,
        session_id: str,
        messages: list[dict[str, Any]],
        *,
        channel_type: str = "",
    ) -> None:
        store = self._get_store(tenant_id, agent_id)
        store.append_messages(session_id, messages, channel_type=channel_type)

    def _get_store(self, tenant_id: str, agent_id: str):
        return ConversationStore(tenant_id=tenant_id, agent_id=agent_id)
