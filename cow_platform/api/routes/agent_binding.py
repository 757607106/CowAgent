from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request

from cow_platform.api.security import MANAGE_ROLES, PlatformAuthorizer
from cow_platform.api.schemas import (
    AgentCreateRequest,
    AgentUpdateRequest,
    BindingCreateRequest,
    BindingUpdateRequest,
)
from cow_platform.services.agent_service import AgentService
from cow_platform.services.binding_service import ChannelBindingService
from cow_platform.services.tenant_service import TenantService


def register_agent_binding_routes(
    app: FastAPI,
    *,
    tenant_service: TenantService,
    agent_service: AgentService,
    binding_service: ChannelBindingService,
    authorizer: PlatformAuthorizer,
    record_audit: Callable[..., None],
) -> None:
    @app.get("/api/platform/agents")
    def list_agents(request: Request, tenant_id: str = "") -> dict[str, object]:
        session = authorizer.require_session(request)
        tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        tenant_service.resolve_tenant(tenant_id)
        return {
            "status": "success",
            "agents": agent_service.list_agent_records(tenant_id),
        }

    @app.get("/api/platform/agents/{agent_id}")
    def get_agent(agent_id: str, request: Request, tenant_id: str = "") -> dict[str, object]:
        session = authorizer.require_session(request)
        tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        tenant_service.resolve_tenant(tenant_id)
        definition = agent_service.resolve_agent(tenant_id=tenant_id, agent_id=agent_id)
        return {
            "status": "success",
            "agent": agent_service.serialize_agent(definition),
        }

    @app.post("/api/platform/agents")
    def create_agent(payload: AgentCreateRequest, request: Request) -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        tenant_id = authorizer.scope_tenant_id(session, payload.tenant_id)
        result = {
            "status": "success",
            "agent": agent_service.create_agent(
                tenant_id=tenant_id,
                agent_id=payload.agent_id,
                name=payload.name,
                model=payload.model,
                model_config_id=payload.model_config_id,
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
    def update_agent(agent_id: str, payload: AgentUpdateRequest, request: Request) -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        tenant_id = authorizer.scope_tenant_id(session, payload.tenant_id)
        tenant_service.resolve_tenant(tenant_id)
        result = {
            "status": "success",
            "agent": agent_service.update_agent(
                agent_id=agent_id,
                tenant_id=tenant_id,
                name=payload.name,
                model=payload.model,
                model_config_id=payload.model_config_id,
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
    def delete_agent(agent_id: str, request: Request, tenant_id: str = "") -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        tenant_service.resolve_tenant(tenant_id)
        deleted = agent_service.delete_agent(agent_id=agent_id, tenant_id=tenant_id)
        record_audit(
            action="delete_agent",
            resource_type="agent",
            resource_id=agent_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
        )
        return {"status": "success", "agent": deleted, "agent_id": agent_id}

    @app.get("/api/platform/bindings")
    def list_bindings(
        request: Request,
        tenant_id: str = "",
        channel_type: str = "",
        channel_config_id: str = "",
    ) -> dict[str, object]:
        session = authorizer.require_session(request)
        tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        return {
            "status": "success",
            "bindings": binding_service.list_binding_records(
                tenant_id=tenant_id,
                channel_type=channel_type,
                channel_config_id=channel_config_id,
            ),
        }

    @app.get("/api/platform/bindings/{binding_id}")
    def get_binding(binding_id: str, request: Request, tenant_id: str = "") -> dict[str, object]:
        session = authorizer.require_session(request)
        tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        try:
            definition = binding_service.resolve_binding(binding_id=binding_id, tenant_id=tenant_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "status": "success",
            "binding": binding_service.serialize_binding(definition),
        }

    @app.post("/api/platform/bindings")
    def create_binding(payload: BindingCreateRequest, request: Request) -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        tenant_id = authorizer.scope_tenant_id(session, payload.tenant_id)
        try:
            binding = binding_service.create_binding(
                tenant_id=tenant_id,
                binding_id=payload.binding_id,
                name=payload.name,
                channel_type=payload.channel_type,
                channel_config_id=payload.channel_config_id,
                agent_id=payload.agent_id,
                enabled=payload.enabled,
                metadata=payload.metadata,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        result = {"status": "success", "binding": binding}
        record_audit(
            action="create_binding",
            resource_type="binding",
            resource_id=result["binding"]["binding_id"],
            tenant_id=result["binding"]["tenant_id"],
            agent_id=result["binding"]["agent_id"],
        )
        return result

    @app.put("/api/platform/bindings/{binding_id}")
    def update_binding(binding_id: str, payload: BindingUpdateRequest, request: Request) -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        tenant_id = authorizer.scope_tenant_id(session, payload.tenant_id or "")
        try:
            binding = binding_service.update_binding(
                binding_id=binding_id,
                tenant_id=tenant_id,
                name=payload.name,
                channel_type=payload.channel_type,
                channel_config_id=payload.channel_config_id,
                agent_id=payload.agent_id,
                enabled=payload.enabled,
                metadata=payload.metadata,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        result = {"status": "success", "binding": binding}
        record_audit(
            action="update_binding",
            resource_type="binding",
            resource_id=binding_id,
            tenant_id=result["binding"]["tenant_id"],
            agent_id=result["binding"]["agent_id"],
        )
        return result

    @app.delete("/api/platform/bindings/{binding_id}")
    def delete_binding(binding_id: str, request: Request, tenant_id: str = "") -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        try:
            binding = binding_service.delete_binding(binding_id=binding_id, tenant_id=tenant_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        result = {"status": "success", "binding": binding}
        record_audit(
            action="delete_binding",
            resource_type="binding",
            resource_id=binding_id,
            tenant_id=result["binding"]["tenant_id"],
            agent_id=result["binding"]["agent_id"],
        )
        return result
