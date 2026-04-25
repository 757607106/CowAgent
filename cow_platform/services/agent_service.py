from __future__ import annotations

from dataclasses import asdict, replace
import os
from pathlib import Path
import secrets
from typing import Any

from config import conf

from cow_platform.domain.models import AgentDefinition
from cow_platform.repositories.agent_repository import AgentRepository
from cow_platform.services.mcp_server_service import TenantMcpServerService
from cow_platform.services.tenant_service import TenantService


DEFAULT_TENANT_ID = "default"
DEFAULT_AGENT_ID = "default"
DEFAULT_AGENT_NAME = "通用 Agent"
LEGACY_DEFAULT_AGENT_NAME = "默认助手"
DEFAULT_NAME_MIGRATED_KEY = "default_name_migrated"


class AgentService:
    """Agent resource service backed by PostgreSQL."""

    def __init__(
        self,
        repository: AgentRepository | None = None,
        tenant_service: TenantService | None = None,
        mcp_server_service: TenantMcpServerService | None = None,
    ):
        self.repository = repository or AgentRepository()
        self.tenant_service = tenant_service or TenantService()
        self.mcp_server_service = mcp_server_service or TenantMcpServerService(tenant_service=self.tenant_service)

    def ensure_default_agent(self, tenant_id: str = DEFAULT_TENANT_ID) -> AgentDefinition:
        self.tenant_service.resolve_tenant(tenant_id)
        existing = self.repository.get_agent(tenant_id, DEFAULT_AGENT_ID)
        if existing:
            return self._normalize_default_agent_name(existing)
        model = os.getenv("MODEL") or conf().get("model", "")
        return self.repository.create_agent(
            tenant_id=tenant_id,
            agent_id=DEFAULT_AGENT_ID,
            name=DEFAULT_AGENT_NAME,
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
        *,
        resolve_mcp: bool = False,
    ) -> AgentDefinition:
        self.ensure_default_agent(tenant_id)
        resolved_agent_id = agent_id or DEFAULT_AGENT_ID
        definition = self.repository.get_agent(tenant_id, resolved_agent_id)
        if definition is None:
            raise KeyError(f"agent not found: {resolved_agent_id}")
        if resolve_mcp:
            return self._with_resolved_mcp_servers(definition)
        return definition

    def create_agent(
        self,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        agent_id: str | None = None,
        name: str,
        model: str = "",
        model_config_id: str = "",
        system_prompt: str = "",
        metadata: dict[str, Any] | None = None,
        tools: tuple[str, ...] | list[str] | None = None,
        skills: tuple[str, ...] | list[str] | None = None,
        knowledge_enabled: bool = False,
        mcp_servers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.tenant_service.resolve_tenant(tenant_id)
        resolved_agent_id = self._resolve_create_agent_id(tenant_id=tenant_id, agent_id=agent_id)
        model, model_config_id = self._normalize_model_selection(
            tenant_id=tenant_id,
            model=model,
            model_config_id=model_config_id,
        )
        definition = self.repository.create_agent(
            tenant_id=tenant_id,
            agent_id=resolved_agent_id,
            name=name,
            model=model,
            model_config_id=model_config_id,
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
        model_config_id: str | None = None,
        system_prompt: str | None = None,
        metadata: dict[str, Any] | None = None,
        tools: tuple[str, ...] | list[str] | None = None,
        skills: tuple[str, ...] | list[str] | None = None,
        knowledge_enabled: bool | None = None,
        mcp_servers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.tenant_service.resolve_tenant(tenant_id)
        model, model_config_id = self._normalize_model_selection(
            tenant_id=tenant_id,
            model=model,
            model_config_id=model_config_id,
            keep_none=True,
        )
        definition = self.repository.update_agent(
            tenant_id=tenant_id,
            agent_id=agent_id,
            name=name,
            model=model,
            model_config_id=model_config_id,
            system_prompt=system_prompt,
            metadata=metadata,
            tools=tools,
            skills=skills,
            knowledge_enabled=knowledge_enabled,
            mcp_servers=mcp_servers,
        )
        return self.serialize_agent(definition)

    def delete_agent(self, agent_id: str, *, tenant_id: str = DEFAULT_TENANT_ID) -> dict[str, Any]:
        if agent_id == DEFAULT_AGENT_ID:
            raise ValueError("default agent cannot be deleted")
        self.tenant_service.resolve_tenant(tenant_id)
        definition = self.repository.delete_agent(tenant_id=tenant_id, agent_id=agent_id)
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

    @staticmethod
    def _normalize_model_selection(
        *,
        tenant_id: str,
        model: str | None,
        model_config_id: str | None,
        keep_none: bool = False,
    ) -> tuple[str | None, str | None]:
        if not model_config_id:
            return (model if model is not None else None, model_config_id if keep_none else "")

        from cow_platform.services.model_config_service import ModelConfigService

        service = ModelConfigService()
        definition = service.resolve_model_for_scope(model_config_id)
        visible = (
            definition.scope == "platform" and definition.is_public
        ) or (
            definition.scope == "tenant" and definition.tenant_id == tenant_id
        )
        if not visible:
            raise PermissionError("model config is not visible to tenant")
        if not definition.enabled:
            raise PermissionError("model config is disabled")
        return (model or definition.model_name, definition.model_config_id)

    def _normalize_default_agent_name(self, definition: AgentDefinition) -> AgentDefinition:
        if definition.agent_id != DEFAULT_AGENT_ID or definition.name != LEGACY_DEFAULT_AGENT_NAME:
            return definition
        metadata = dict(definition.metadata or {})
        if metadata.get(DEFAULT_NAME_MIGRATED_KEY):
            return definition
        metadata[DEFAULT_NAME_MIGRATED_KEY] = True
        return self.repository.update_agent(
            tenant_id=definition.tenant_id,
            agent_id=definition.agent_id,
            name=DEFAULT_AGENT_NAME,
            metadata=metadata,
        )

    def _with_resolved_mcp_servers(self, definition: AgentDefinition) -> AgentDefinition:
        resolved_servers = self.mcp_server_service.resolve_bound_servers(
            definition.tenant_id,
            dict(definition.mcp_servers or {}),
        )
        return replace(definition, mcp_servers=resolved_servers)
