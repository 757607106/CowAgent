from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request

from cow_platform.api.schemas import ChannelConfigCreateRequest, ChannelConfigUpdateRequest
from cow_platform.api.security import MANAGE_ROLES, PlatformAuthorizer
from cow_platform.services.channel_config_service import ChannelConfigService


def register_channel_config_routes(
    app: FastAPI,
    *,
    channel_config_service: ChannelConfigService,
    authorizer: PlatformAuthorizer,
    record_audit: Callable[..., None],
) -> None:
    @app.get("/api/platform/channel-configs")
    def list_channel_configs(
        request: Request,
        tenant_id: str = "",
        channel_type: str = "",
    ) -> dict[str, object]:
        session = authorizer.require_session(request)
        scoped_tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        return {
            "status": "success",
            "channel_types": channel_config_service.list_channel_type_defs(),
            "channel_configs": [
                channel_config_service.serialize_channel_config(item)
                for item in channel_config_service.list_channel_configs(
                    tenant_id=scoped_tenant_id,
                    channel_type=channel_type,
                )
            ],
        }

    @app.post("/api/platform/channel-configs")
    def create_channel_config(payload: ChannelConfigCreateRequest, request: Request) -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        scoped_tenant_id = authorizer.scope_tenant_id(session, payload.tenant_id)
        try:
            channel_config = channel_config_service.create_channel_config(
                tenant_id=scoped_tenant_id,
                channel_config_id=payload.channel_config_id,
                name=payload.name,
                channel_type=payload.channel_type,
                config=payload.config,
                enabled=payload.enabled,
                metadata=payload.metadata,
                created_by=session.user_id,
            )
            record_audit(
                action="tenant_create_channel_config",
                resource_type="channel_config",
                resource_id=channel_config["channel_config_id"],
                tenant_id=scoped_tenant_id,
                metadata={"channel_type": channel_config["channel_type"]},
            )
            return {"status": "success", "channel_config": channel_config}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/platform/channel-configs/{channel_config_id}")
    def get_channel_config(channel_config_id: str, request: Request, tenant_id: str = "") -> dict[str, object]:
        session = authorizer.require_session(request)
        scoped_tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        try:
            definition = channel_config_service.resolve_channel_config(
                tenant_id=scoped_tenant_id,
                channel_config_id=channel_config_id,
            )
            return {
                "status": "success",
                "channel_config": channel_config_service.serialize_channel_config(definition),
            }
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.put("/api/platform/channel-configs/{channel_config_id}")
    def update_channel_config(
        channel_config_id: str,
        payload: ChannelConfigUpdateRequest,
        request: Request,
    ) -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        scoped_tenant_id = authorizer.scope_tenant_id(session, payload.tenant_id or "")
        try:
            channel_config = channel_config_service.update_channel_config(
                channel_config_id=channel_config_id,
                tenant_id=scoped_tenant_id,
                name=payload.name,
                channel_type=payload.channel_type,
                config=payload.config,
                enabled=payload.enabled,
                metadata=payload.metadata,
            )
            record_audit(
                action="tenant_update_channel_config",
                resource_type="channel_config",
                resource_id=channel_config_id,
                tenant_id=scoped_tenant_id,
                metadata={"channel_type": channel_config["channel_type"]},
            )
            return {"status": "success", "channel_config": channel_config}
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/api/platform/channel-configs/{channel_config_id}")
    def delete_channel_config(channel_config_id: str, request: Request, tenant_id: str = "") -> dict[str, object]:
        session = authorizer.require_session(request, roles=MANAGE_ROLES)
        scoped_tenant_id = authorizer.scope_tenant_id(session, tenant_id)
        try:
            channel_config = channel_config_service.delete_channel_config(
                channel_config_id=channel_config_id,
                tenant_id=scoped_tenant_id,
            )
            record_audit(
                action="tenant_delete_channel_config",
                resource_type="channel_config",
                resource_id=channel_config_id,
                tenant_id=scoped_tenant_id,
                metadata={"channel_type": channel_config["channel_type"]},
            )
            return {"status": "success", "channel_config": channel_config}
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
