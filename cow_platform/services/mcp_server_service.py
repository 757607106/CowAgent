from __future__ import annotations

from typing import Any

from cow_platform.domain.models import TenantMcpServerDefinition
from cow_platform.repositories.mcp_server_repository import TenantMcpServerRepository
from cow_platform.services.tenant_service import TenantService

DEFAULT_TENANT_ID = "default"


class TenantMcpServerService:
    """Tenant-level MCP configuration service."""

    def __init__(
        self,
        repository: TenantMcpServerRepository | None = None,
        tenant_service: TenantService | None = None,
    ) -> None:
        self.repository = repository or TenantMcpServerRepository()
        self.tenant_service = tenant_service or TenantService()

    def list_servers(self, tenant_id: str = DEFAULT_TENANT_ID) -> list[dict[str, Any]]:
        self.tenant_service.resolve_tenant(tenant_id)
        return [self.serialize_server(server) for server in self.repository.list_servers(tenant_id)]

    def get_server(self, tenant_id: str, name: str) -> TenantMcpServerDefinition:
        self.tenant_service.resolve_tenant(tenant_id)
        normalized_name = self._normalize_name(name)
        server = self.repository.get_server(tenant_id, normalized_name)
        if server is None:
            raise KeyError(f"mcp server not found: {normalized_name}")
        return server

    def save_server(
        self,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        name: str,
        command: str,
        args: list[str] | tuple[str, ...] | None = None,
        env: dict[str, str] | None = None,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.tenant_service.resolve_tenant(tenant_id)
        normalized_name = self._normalize_name(name)
        normalized_command = str(command or "").strip()
        if not normalized_command:
            raise ValueError("command is required")
        server = self.repository.upsert_server(
            tenant_id=tenant_id,
            name=normalized_name,
            command=normalized_command,
            args=[str(item) for item in (args or [])],
            env={str(key): str(value) for key, value in (env or {}).items() if str(key).strip()},
            enabled=bool(enabled),
            metadata=metadata or {},
        )
        return self.serialize_server(server)

    def delete_server(self, *, tenant_id: str = DEFAULT_TENANT_ID, name: str) -> dict[str, Any]:
        self.tenant_service.resolve_tenant(tenant_id)
        server = self.repository.delete_server(tenant_id, self._normalize_name(name))
        return self.serialize_server(server)

    def resolve_bound_servers(
        self,
        tenant_id: str,
        bindings: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        catalog = {server.name: self.serialize_server(server) for server in self.repository.list_servers(tenant_id)}
        resolved: dict[str, dict[str, Any]] = {}

        for name, binding in (bindings or {}).items():
            if not isinstance(binding, dict):
                binding = {}
            if not binding.get("enabled", True):
                continue

            configured = catalog.get(name)
            if configured:
                if not configured.get("enabled", True):
                    continue
                resolved[name] = {
                    "command": configured.get("command", ""),
                    "args": configured.get("args", []),
                    "env": configured.get("env", {}),
                    "enabled": True,
                }
                continue

            # Backward compatibility for old agent-local MCP configs. New writes
            # only store bindings, but existing rows can still run until migrated.
            if binding.get("command"):
                resolved[name] = {
                    "command": binding.get("command", ""),
                    "args": binding.get("args", []),
                    "env": binding.get("env", {}),
                    "enabled": True,
                }

        return resolved

    @staticmethod
    def serialize_server(definition: TenantMcpServerDefinition) -> dict[str, Any]:
        return {
            "tenant_id": definition.tenant_id,
            "name": definition.name,
            "command": definition.command,
            "args": list(definition.args),
            "env": dict(definition.env),
            "enabled": definition.enabled,
            "metadata": dict(definition.metadata),
        }

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = str(name or "").strip()
        if not normalized:
            raise ValueError("name is required")
        return normalized
