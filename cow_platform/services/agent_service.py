from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
import secrets
from typing import Any

from config import conf

from cow_platform.domain.models import AgentDefinition
from cow_platform.repositories.agent_repository import FileAgentRepository
from cow_platform.services.tenant_service import TenantService


DEFAULT_TENANT_ID = "default"
DEFAULT_AGENT_ID = "default"


class AgentService:
    """单租户阶段使用的 Agent 服务。"""

    def __init__(
        self,
        repository: FileAgentRepository | None = None,
        tenant_service: TenantService | None = None,
    ):
        self.repository = repository or FileAgentRepository()
        self.tenant_service = tenant_service or TenantService()

    def ensure_default_agent(self, tenant_id: str = DEFAULT_TENANT_ID) -> AgentDefinition:
        self.tenant_service.resolve_tenant(tenant_id)
        existing = self.repository.get_agent(tenant_id, DEFAULT_AGENT_ID)
        if existing:
            return existing
        model = os.getenv("MODEL") or conf().get("model", "")
        return self.repository.create_agent(
            tenant_id=tenant_id,
            agent_id=DEFAULT_AGENT_ID,
            name="默认助手",
            model=model,
            system_prompt="",
            knowledge_enabled=bool(conf().get("knowledge", True)),
            metadata={"source": "legacy-default"},
        )

    def list_agents(self, tenant_id: str = DEFAULT_TENANT_ID) -> list[AgentDefinition]:
        self.ensure_default_agent(tenant_id)
        return self.repository.list_agents(tenant_id)

    def get_agent(self, tenant_id: str, agent_id: str) -> AgentDefinition | None:
        return self.repository.get_agent(tenant_id, agent_id)

    def resolve_agent(
        self,
        tenant_id: str = DEFAULT_TENANT_ID,
        agent_id: str | None = None,
    ) -> AgentDefinition:
        self.ensure_default_agent(tenant_id)
        resolved_agent_id = agent_id or DEFAULT_AGENT_ID
        definition = self.repository.get_agent(tenant_id, resolved_agent_id)
        if definition is None:
            raise KeyError(f"agent not found: {resolved_agent_id}")
        return definition

    def create_agent(
        self,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        agent_id: str | None = None,
        name: str,
        model: str = "",
        system_prompt: str = "",
        metadata: dict[str, Any] | None = None,
        tools: tuple[str, ...] | list[str] | None = None,
        skills: tuple[str, ...] | list[str] | None = None,
        knowledge_enabled: bool = False,
        mcp_servers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.tenant_service.resolve_tenant(tenant_id)
        resolved_agent_id = self._resolve_create_agent_id(tenant_id=tenant_id, agent_id=agent_id)
        definition = self.repository.create_agent(
            tenant_id=tenant_id,
            agent_id=resolved_agent_id,
            name=name,
            model=model,
            system_prompt=system_prompt,
            metadata=metadata or {},
            tools=tools,
            skills=skills,
            knowledge_enabled=knowledge_enabled,
            mcp_servers=mcp_servers,
        )
        return self.serialize_agent(definition)

    def update_agent(
        self,
        agent_id: str,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        name: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        metadata: dict[str, Any] | None = None,
        tools: tuple[str, ...] | list[str] | None = None,
        skills: tuple[str, ...] | list[str] | None = None,
        knowledge_enabled: bool | None = None,
        mcp_servers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.tenant_service.resolve_tenant(tenant_id)
        definition = self.repository.update_agent(
            tenant_id=tenant_id,
            agent_id=agent_id,
            name=name,
            model=model,
            system_prompt=system_prompt,
            metadata=metadata,
            tools=tools,
            skills=skills,
            knowledge_enabled=knowledge_enabled,
            mcp_servers=mcp_servers,
        )
        return self.serialize_agent(definition)

    def get_agent_workspace(self, tenant_id: str, agent_id: str) -> Path:
        return self.repository.get_workspace_path(tenant_id, agent_id)

    def serialize_agent(self, definition: AgentDefinition) -> dict[str, Any]:
        record = self.repository.export_record(definition)
        record["workspace_path"] = str(self.get_agent_workspace(definition.tenant_id, definition.agent_id))
        return record

    def list_agent_records(self, tenant_id: str = DEFAULT_TENANT_ID) -> list[dict[str, Any]]:
        return [self.serialize_agent(item) for item in self.list_agents(tenant_id)]

    def _resolve_create_agent_id(self, *, tenant_id: str, agent_id: str | None) -> str:
        candidate = str(agent_id or "").strip()
        if candidate:
            return candidate
        return self._generate_agent_id(tenant_id)

    def _generate_agent_id(self, tenant_id: str) -> str:
        for _ in range(20):
            # 8 hex chars keeps ids short while maintaining practical uniqueness.
            candidate = f"agt_{secrets.token_hex(4)}"
            if self.repository.get_agent(tenant_id, candidate) is None:
                return candidate
        raise RuntimeError("unable to generate unique agent_id")
