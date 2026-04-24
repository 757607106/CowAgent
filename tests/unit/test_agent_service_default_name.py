from pathlib import Path

from cow_platform.domain.models import AgentDefinition
from cow_platform.services.agent_service import (
    DEFAULT_AGENT_ID,
    DEFAULT_AGENT_NAME,
    DEFAULT_NAME_MIGRATED_KEY,
    LEGACY_DEFAULT_AGENT_NAME,
    AgentService,
)


class _TenantService:
    def resolve_tenant(self, tenant_id):
        return {"tenant_id": tenant_id}


class _AgentRepository:
    def __init__(self, agent=None):
        self.agent = agent
        self.updated_payloads = []

    def get_agent(self, tenant_id, agent_id):
        if self.agent and self.agent.tenant_id == tenant_id and self.agent.agent_id == agent_id:
            return self.agent
        return None

    def create_agent(self, **kwargs):
        self.agent = AgentDefinition(
            tenant_id=kwargs["tenant_id"],
            agent_id=kwargs["agent_id"],
            name=kwargs["name"],
            model=kwargs.get("model", ""),
            system_prompt=kwargs.get("system_prompt", ""),
            metadata=kwargs.get("metadata") or {},
            tools=tuple(kwargs.get("tools") or ()),
            skills=tuple(kwargs.get("skills") or ()),
            knowledge_enabled=bool(kwargs.get("knowledge_enabled", False)),
            mcp_servers=kwargs.get("mcp_servers") or {},
        )
        return self.agent

    def update_agent(self, tenant_id, agent_id, **kwargs):
        self.updated_payloads.append({"tenant_id": tenant_id, "agent_id": agent_id, **kwargs})
        self.agent = AgentDefinition(
            tenant_id=tenant_id,
            agent_id=agent_id,
            name=kwargs.get("name", self.agent.name),
            version=self.agent.version + 1,
            model=kwargs.get("model", self.agent.model),
            system_prompt=kwargs.get("system_prompt", self.agent.system_prompt),
            metadata=kwargs.get("metadata", self.agent.metadata),
            tools=tuple(kwargs.get("tools", self.agent.tools)),
            skills=tuple(kwargs.get("skills", self.agent.skills)),
            knowledge_enabled=kwargs.get("knowledge_enabled", self.agent.knowledge_enabled),
            mcp_servers=kwargs.get("mcp_servers", self.agent.mcp_servers),
        )
        return self.agent

    def get_workspace_path(self, tenant_id, agent_id):
        return Path("/tmp") / tenant_id / agent_id

    def export_record(self, definition):
        return {
            "tenant_id": definition.tenant_id,
            "agent_id": definition.agent_id,
            "name": definition.name,
            "version": definition.version,
            "metadata": dict(definition.metadata),
            "tools": list(definition.tools),
            "skills": list(definition.skills),
            "knowledge_enabled": definition.knowledge_enabled,
            "mcp_servers": dict(definition.mcp_servers),
        }


def test_new_default_agent_is_named_generic_agent():
    repository = _AgentRepository()
    service = AgentService(repository=repository, tenant_service=_TenantService())

    agent = service.ensure_default_agent("tenant-a")

    assert agent.agent_id == DEFAULT_AGENT_ID
    assert agent.name == DEFAULT_AGENT_NAME


def test_legacy_default_agent_name_is_migrated_once():
    repository = _AgentRepository(AgentDefinition(
        tenant_id="tenant-a",
        agent_id=DEFAULT_AGENT_ID,
        name=LEGACY_DEFAULT_AGENT_NAME,
        metadata={"source": "legacy-default"},
    ))
    service = AgentService(repository=repository, tenant_service=_TenantService())

    agent = service.ensure_default_agent("tenant-a")

    assert agent.name == DEFAULT_AGENT_NAME
    assert agent.metadata[DEFAULT_NAME_MIGRATED_KEY] is True
    assert repository.updated_payloads[0]["name"] == DEFAULT_AGENT_NAME


def test_migrated_default_agent_can_be_renamed_to_any_name():
    repository = _AgentRepository(AgentDefinition(
        tenant_id="tenant-a",
        agent_id=DEFAULT_AGENT_ID,
        name=LEGACY_DEFAULT_AGENT_NAME,
        metadata={DEFAULT_NAME_MIGRATED_KEY: True},
    ))
    service = AgentService(repository=repository, tenant_service=_TenantService())

    agent = service.ensure_default_agent("tenant-a")

    assert agent.name == LEGACY_DEFAULT_AGENT_NAME
    assert repository.updated_payloads == []
