from __future__ import annotations

from typing import Any


def _core() -> Any:
    from channel.web import web_channel

    return web_channel


def _register_platform_admin(data: dict[str, object]) -> dict[str, object]:
    return _core()._register_platform_admin(data)


def _require_auth() -> None:
    return _core()._require_auth()


def _require_platform_admin() -> None:
    return _core()._require_platform_admin()


def _require_tenant_manage() -> None:
    return _core()._require_tenant_manage()


def _raise_forbidden(message: str = "Forbidden") -> None:
    return _core()._raise_forbidden(message)


def _is_tenant_auth_enabled() -> bool:
    return _core()._is_tenant_auth_enabled()


def _is_platform_admin_session(session: Any = None) -> bool:
    return _core()._is_platform_admin_session(session)


def _get_authenticated_tenant_session() -> Any:
    return _core()._get_authenticated_tenant_session()


def _parse_bool(value: Any, default: bool = True) -> bool:
    return _core()._parse_bool(value, default)


def _scope_tenant_id(tenant_id: str = "", *, default: str = "default") -> str:
    return _core()._scope_tenant_id(tenant_id, default=default)


def _scope_optional_tenant_id(tenant_id: str = "") -> str:
    return _core()._scope_optional_tenant_id(tenant_id)


def _get_agent_service() -> Any:
    return _core()._get_agent_service()


def _get_mcp_server_service() -> Any:
    return _core()._get_mcp_server_service()


def _get_tenant_service() -> Any:
    return _core()._get_tenant_service()


def _get_tenant_user_service() -> Any:
    return _core()._get_tenant_user_service()


def _get_model_config_service() -> Any:
    return _core()._get_model_config_service()


def _get_channel_config_service() -> Any:
    return _core()._get_channel_config_service()


def _get_binding_service() -> Any:
    return _core()._get_binding_service()


def _get_usage_service() -> Any:
    return _core()._get_usage_service()


def _get_session_repository() -> Any:
    return _core()._get_session_repository()


def _get_runtime_adapter() -> Any:
    return _core()._get_runtime_adapter()


def _restart_channel_config_runtime(channel_config_id: str) -> None:
    return _core()._restart_channel_config_runtime(channel_config_id)


def _stop_channel_config_runtime(channel_config_id: str) -> None:
    return _core()._stop_channel_config_runtime(channel_config_id)


def _resolve_runtime_target(agent_id: str = "", tenant_id: str = "", binding_id: str = "") -> dict[str, str]:
    return _core()._resolve_runtime_target(agent_id=agent_id, tenant_id=tenant_id, binding_id=binding_id)


def _get_session_store(agent_id: str = "", tenant_id: str = "", binding_id: str = "") -> Any:
    return _core()._get_session_store(agent_id=agent_id, tenant_id=tenant_id, binding_id=binding_id)


def _generate_session_title(user_message: str, assistant_reply: str = "") -> str:
    return _core()._generate_session_title(user_message, assistant_reply)


def _get_workspace_root(agent_id: str = "", tenant_id: str = "", binding_id: str = "") -> str:
    return _core()._get_workspace_root(agent_id=agent_id, tenant_id=tenant_id, binding_id=binding_id)


def _is_knowledge_enabled(agent_id: str = "", tenant_id: str = "", binding_id: str = "") -> bool:
    return _core()._is_knowledge_enabled(agent_id=agent_id, tenant_id=tenant_id, binding_id=binding_id)


def WebChannel() -> Any:
    return _core().WebChannel()


__all__ = [
    "WebChannel",
    "_generate_session_title",
    "_get_agent_service",
    "_get_authenticated_tenant_session",
    "_get_binding_service",
    "_get_channel_config_service",
    "_get_mcp_server_service",
    "_get_model_config_service",
    "_get_runtime_adapter",
    "_get_session_repository",
    "_get_session_store",
    "_get_tenant_service",
    "_get_tenant_user_service",
    "_get_usage_service",
    "_get_workspace_root",
    "_is_knowledge_enabled",
    "_is_platform_admin_session",
    "_is_tenant_auth_enabled",
    "_parse_bool",
    "_raise_forbidden",
    "_register_platform_admin",
    "_require_auth",
    "_require_platform_admin",
    "_require_tenant_manage",
    "_resolve_runtime_target",
    "_restart_channel_config_runtime",
    "_scope_optional_tenant_id",
    "_scope_tenant_id",
    "_stop_channel_config_runtime",
]
