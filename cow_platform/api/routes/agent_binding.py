from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI

from cow_platform.api.schemas import (
    AgentCreateRequest,
    AgentUpdateRequest,
    BindingCreateRequest,
    BindingUpdateRequest,
)
from cow_platform.services.agent_service import AgentService, DEFAULT_TENANT_ID
from cow_platform.services.binding_service import ChannelBindingService
from cow_platform.services.tenant_service import TenantService


def register_agent_binding_routes(
    app: FastAPI,
    *,
    tenant_service: TenantService,
    agent_service: AgentService,
    binding_service: ChannelBindingService,
    record_audit: Callable[..., None],
) -> None:
    @app.get("/api/platform/agents")
    def list_agents(tenant_id: str = DEFAULT_TENANT_ID) -> dict[str, object]:
        tenant_service.resolve_tenant(tenant_id)
        return {
            "status": "success",
            "agents": agent_service.list_agent_records(tenant_id),
        }

    @app.get("/api/platform/agents/{agent_id}")
    def get_agent(agent_id: str, tenant_id: str = DEFAULT_TENANT_ID) -> dict[str, object]:
        tenant_service.resolve_tenant(tenant_id)
        definition = agent_service.resolve_agent(tenant_id=tenant_id, agent_id=agent_id)
        return {
            "status": "success",
            "agent": agent_service.serialize_agent(definition),
        }

    @app.post("/api/platform/agents")
    def create_agent(payload: AgentCreateRequest) -> dict[str, object]:
        result = {
            "status": "success",
            "agent": agent_service.create_agent(
                tenant_id=payload.tenant_id,
                agent_id=payload.agent_id,
                name=payload.name,
                model=payload.model,
                system_prompt=payload.system_prompt,
                tools=payload.tools,
                skills=payload.skills,
                knowledge_enabled=payload.knowledge_enabled,
                mcp_servers=payload.mcp_servers,
            ),
        }
        record_audit(
            action="create_agent",
            resource_type="agent",
            resource_id=result["agent"]["agent_id"],
            tenant_id=result["agent"]["tenant_id"],
            agent_id=result["agent"]["agent_id"],
        )
        return result

    @app.put("/api/platform/agents/{agent_id}")
    def update_agent(agent_id: str, payload: AgentUpdateRequest) -> dict[str, object]:
        tenant_service.resolve_tenant(payload.tenant_id)
        result = {
            "status": "success",
            "agent": agent_service.update_agent(
                agent_id=agent_id,
                tenant_id=payload.tenant_id,
                name=payload.name,
                model=payload.model,
                system_prompt=payload.system_prompt,
                tools=payload.tools,
                skills=payload.skills,
                knowledge_enabled=payload.knowledge_enabled,
                mcp_servers=payload.mcp_servers,
            ),
        }
        # Runtime config changed: invalidate cached agent instances for this tenant-agent
        # so the next message uses the latest prompt/tool/skill/knowledge/mcp settings.
        try:
            from bridge.bridge import Bridge

            Bridge().get_agent_bridge().clear_agent_sessions(
                tenant_id=result["agent"]["tenant_id"],
                agent_id=agent_id,
            )
        except Exception:
            pass
        record_audit(
            action="update_agent",
            resource_type="agent",
            resource_id=agent_id,
            tenant_id=result["agent"]["tenant_id"],
            agent_id=agent_id,
        )
        return result

    @app.delete("/api/platform/agents/{agent_id}")
    def delete_agent(agent_id: str, tenant_id: str = DEFAULT_TENANT_ID) -> dict[str, object]:
        tenant_service.resolve_tenant(tenant_id)
        agent_service.resolve_agent(tenant_id=tenant_id, agent_id=agent_id)
        repository = agent_service.repository
        key = repository._build_key(tenant_id, agent_id)
        with repository._lock:
            store = repository._load_store()
            if key not in store["agents"]:
                raise KeyError(f"agent not found: {agent_id}")
            del store["agents"][key]
            repository._save_store(store)
        record_audit(
            action="delete_agent",
            resource_type="agent",
            resource_id=agent_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
        )
        return {"status": "success", "agent_id": agent_id}

    @app.get("/api/platform/bindings")
    def list_bindings(tenant_id: str = "", channel_type: str = "") -> dict[str, object]:
        return {
            "status": "success",
            "bindings": binding_service.list_binding_records(
                tenant_id=tenant_id,
                channel_type=channel_type,
            ),
        }

    @app.get("/api/platform/bindings/{binding_id}")
    def get_binding(binding_id: str, tenant_id: str = "") -> dict[str, object]:
        definition = binding_service.resolve_binding(binding_id=binding_id, tenant_id=tenant_id)
        return {
            "status": "success",
            "binding": binding_service.serialize_binding(definition),
        }

    @app.post("/api/platform/bindings")
    def create_binding(payload: BindingCreateRequest) -> dict[str, object]:
        result = {
            "status": "success",
            "binding": binding_service.create_binding(
                tenant_id=payload.tenant_id,
                binding_id=payload.binding_id,
                name=payload.name,
                channel_type=payload.channel_type,
                agent_id=payload.agent_id,
                enabled=payload.enabled,
                metadata=payload.metadata,
            ),
        }
        record_audit(
            action="create_binding",
            resource_type="binding",
            resource_id=result["binding"]["binding_id"],
            tenant_id=result["binding"]["tenant_id"],
            agent_id=result["binding"]["agent_id"],
        )
        return result

    @app.put("/api/platform/bindings/{binding_id}")
    def update_binding(binding_id: str, payload: BindingUpdateRequest) -> dict[str, object]:
        result = {
            "status": "success",
            "binding": binding_service.update_binding(
                binding_id=binding_id,
                tenant_id=payload.tenant_id or "",
                name=payload.name,
                channel_type=payload.channel_type,
                agent_id=payload.agent_id,
                enabled=payload.enabled,
                metadata=payload.metadata,
            ),
        }
        record_audit(
            action="update_binding",
            resource_type="binding",
            resource_id=binding_id,
            tenant_id=result["binding"]["tenant_id"],
            agent_id=result["binding"]["agent_id"],
        )
        return result

    @app.delete("/api/platform/bindings/{binding_id}")
    def delete_binding(binding_id: str, tenant_id: str = "") -> dict[str, object]:
        result = {
            "status": "success",
            "binding": binding_service.delete_binding(binding_id=binding_id, tenant_id=tenant_id),
        }
        record_audit(
            action="delete_binding",
            resource_type="binding",
            resource_id=binding_id,
            tenant_id=result["binding"]["tenant_id"],
            agent_id=result["binding"]["agent_id"],
        )
        return result
