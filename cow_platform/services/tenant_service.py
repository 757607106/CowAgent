from __future__ import annotations

from typing import Any

from cow_platform.domain.models import TenantDefinition
from cow_platform.repositories.tenant_repository import FileTenantRepository


DEFAULT_TENANT_ID = "default"


class TenantService:
    """当前阶段使用的租户服务。"""

    def __init__(self, repository: FileTenantRepository | None = None):
        self.repository = repository or FileTenantRepository()

    def ensure_default_tenant(self) -> TenantDefinition:
        existing = self.repository.get_tenant(DEFAULT_TENANT_ID)
        if existing:
            return existing
        return self.repository.create_tenant(
            tenant_id=DEFAULT_TENANT_ID,
            name="默认租户",
            status="active",
            metadata={"source": "legacy-default"},
        )

    def list_tenants(self) -> list[TenantDefinition]:
        self.ensure_default_tenant()
        return self.repository.list_tenants()

    def resolve_tenant(self, tenant_id: str = DEFAULT_TENANT_ID) -> TenantDefinition:
        self.ensure_default_tenant()
        definition = self.repository.get_tenant(tenant_id)
        if definition is None:
            raise KeyError(f"tenant not found: {tenant_id}")
        return definition

    def create_tenant(
        self,
        *,
        tenant_id: str,
        name: str,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        definition = self.repository.create_tenant(
            tenant_id=tenant_id,
            name=name,
            status=status,
            metadata=metadata or {},
        )
        return self.serialize_tenant(definition)

    def update_tenant(
        self,
        tenant_id: str,
        *,
        name: str | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        definition = self.repository.update_tenant(
            tenant_id=tenant_id,
            name=name,
            status=status,
            metadata=metadata,
        )
        return self.serialize_tenant(definition)

    def serialize_tenant(self, definition: TenantDefinition) -> dict[str, Any]:
        return self.repository.export_record(definition)

    def list_tenant_records(self) -> list[dict[str, Any]]:
        return [self.serialize_tenant(item) for item in self.list_tenants()]
