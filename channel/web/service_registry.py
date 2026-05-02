from __future__ import annotations

from typing import Callable

from common.log import logger


def get_auth_service(*, session_expire_seconds: int):
    from cow_platform.services.auth_service import TenantAuthService

    return TenantAuthService(session_expire_seconds=session_expire_seconds)


def get_agent_service():
    from cow_platform.services.agent_service import AgentService

    return AgentService()


def get_mcp_server_service():
    from cow_platform.services.mcp_server_service import TenantMcpServerService

    return TenantMcpServerService()


def get_tenant_service():
    from cow_platform.services.tenant_service import TenantService

    return TenantService()


def get_tenant_user_service():
    from cow_platform.services.tenant_user_service import TenantUserService

    return TenantUserService()


def get_model_config_service():
    from cow_platform.services.model_config_service import ModelConfigService

    return ModelConfigService()


def get_channel_config_service():
    from cow_platform.services.channel_config_service import ChannelConfigService

    return ChannelConfigService()


def get_binding_service():
    from cow_platform.services.binding_service import ChannelBindingService

    return ChannelBindingService()


def get_usage_service():
    from cow_platform.services.usage_service import UsageService

    return UsageService()


def get_session_repository():
    from cow_platform.repositories.session_repository import SessionRepository

    return SessionRepository()


def get_runtime_adapter():
    from cow_platform.adapters.cowagent_runtime_adapter import CowAgentRuntimeAdapter

    return CowAgentRuntimeAdapter()


def restart_channel_config_runtime(
    channel_config_id: str,
    *,
    channel_config_service_factory: Callable[[], object] = get_channel_config_service,
) -> None:
    try:
        from cow_platform.runtime.channel_manager import get_channel_manager

        mgr = get_channel_manager()
        if not mgr:
            return
        definition = channel_config_service_factory().resolve_channel_config(
            channel_config_id=channel_config_id,
        )
        if definition.enabled:
            mgr.start_channel_config(definition)
        else:
            mgr.remove_channel_config(channel_config_id)
    except Exception as e:
        logger.warning(f"[WebChannel] channel config runtime refresh skipped: {e}")


def stop_channel_config_runtime(channel_config_id: str) -> None:
    try:
        from cow_platform.runtime.channel_manager import get_channel_manager

        mgr = get_channel_manager()
        if mgr:
            mgr.remove_channel_config(channel_config_id)
    except Exception as e:
        logger.warning(f"[WebChannel] channel config runtime stop skipped: {e}")
