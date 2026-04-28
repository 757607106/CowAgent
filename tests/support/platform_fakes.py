from __future__ import annotations

import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from cow_platform.domain.models import (
    AgentDefinition,
    AuditLogRecord,
    ChannelBindingDefinition,
    JobDefinition,
    PricingDefinition,
    QuotaDefinition,
    TenantDefinition,
    TenantMcpServerDefinition,
    TenantUserDefinition,
    TenantUserIdentityDefinition,
    UsageRecord,
)


class InMemoryTenantRepository:
    def __init__(self) -> None:
        self.tenants: dict[str, TenantDefinition] = {}
        self.timestamps: dict[str, tuple[int, int]] = {}

    def list_tenants(self) -> list[TenantDefinition]:
        return sorted(self.tenants.values(), key=lambda item: item.tenant_id)

    def get_tenant(self, tenant_id: str) -> TenantDefinition | None:
        return self.tenants.get(tenant_id)

    def create_tenant(
        self,
        tenant_id: str,
        name: str,
        *,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> TenantDefinition:
        if tenant_id in self.tenants:
            raise ValueError(f"tenant already exists: {tenant_id}")
        now = int(time.time())
        definition = TenantDefinition(
            tenant_id=tenant_id,
            name=name,
            status=status,
            metadata=dict(metadata or {}),
        )
        self.tenants[tenant_id] = definition
        self.timestamps[tenant_id] = (now, now)
        return definition

    def update_tenant(
        self,
        tenant_id: str,
        *,
        name: str | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TenantDefinition:
        current = self.tenants.get(tenant_id)
        if current is None:
            raise KeyError(f"tenant not found: {tenant_id}")
        created_at, _ = self.timestamps.get(tenant_id, (None, None))
        definition = TenantDefinition(
            tenant_id=tenant_id,
            name=current.name if name is None else name,
            status=current.status if status is None else status,
            metadata=dict(current.metadata if metadata is None else metadata),
        )
        self.tenants[tenant_id] = definition
        self.timestamps[tenant_id] = (created_at, int(time.time()))
        return definition

    def delete_tenant(self, tenant_id: str) -> TenantDefinition:
        return self.update_tenant(tenant_id, status="deleted")

    def export_record(self, definition: TenantDefinition) -> dict[str, Any]:
        created_at, updated_at = self.timestamps.get(definition.tenant_id, (None, None))
        return {
            "tenant_id": definition.tenant_id,
            "name": definition.name,
            "status": definition.status,
            "metadata": dict(definition.metadata),
            "created_at": created_at,
            "updated_at": updated_at,
        }


class InMemoryTenantUserRepository:
    def __init__(self) -> None:
        self.users: dict[tuple[str, str], TenantUserDefinition] = {}
        self.identities: dict[tuple[str, str, str], TenantUserIdentityDefinition] = {}

    def list_users(
        self,
        *,
        tenant_id: str = "",
        role: str = "",
        status: str = "",
    ) -> list[TenantUserDefinition]:
        users = list(self.users.values())
        if tenant_id:
            users = [user for user in users if user.tenant_id == tenant_id]
        if role:
            users = [user for user in users if user.role == role]
        if status:
            users = [user for user in users if user.status == status]
        return sorted(users, key=lambda item: (item.tenant_id, item.user_id))

    def get_user(self, tenant_id: str, user_id: str) -> TenantUserDefinition | None:
        return self.users.get((tenant_id, user_id))

    def create_user(
        self,
        *,
        tenant_id: str,
        user_id: str,
        name: str = "",
        role: str,
        status: str = "active",
        metadata: dict[str, Any] | None = None,
    ) -> TenantUserDefinition:
        key = (tenant_id, user_id)
        if key in self.users:
            raise ValueError(f"tenant user already exists: {tenant_id}/{user_id}")
        definition = TenantUserDefinition(
            tenant_id=tenant_id,
            user_id=user_id,
            name=name,
            role=role,
            status=status,
            metadata=dict(metadata or {}),
        )
        self.users[key] = definition
        return definition

    def update_user(
        self,
        *,
        tenant_id: str,
        user_id: str,
        name: str | None = None,
        role: str | None = None,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TenantUserDefinition:
        current = self.users.get((tenant_id, user_id))
        if current is None:
            raise KeyError(f"tenant user not found: {tenant_id}/{user_id}")
        definition = TenantUserDefinition(
            tenant_id=tenant_id,
            user_id=user_id,
            name=current.name if name is None else name,
            role=current.role if role is None else role,
            status=current.status if status is None else status,
            metadata=dict(current.metadata if metadata is None else metadata),
        )
        self.users[(tenant_id, user_id)] = definition
        return definition

    def delete_user(self, *, tenant_id: str, user_id: str) -> TenantUserDefinition:
        key = (tenant_id, user_id)
        current = self.users.pop(key, None)
        if current is None:
            raise KeyError(f"tenant user not found: {tenant_id}/{user_id}")
        self.identities = {
            identity_key: identity
            for identity_key, identity in self.identities.items()
            if not (identity.tenant_id == tenant_id and identity.user_id == user_id)
        }
        return current

    def list_identities(
        self,
        *,
        tenant_id: str = "",
        user_id: str = "",
        channel_type: str = "",
    ) -> list[TenantUserIdentityDefinition]:
        identities = list(self.identities.values())
        if tenant_id:
            identities = [item for item in identities if item.tenant_id == tenant_id]
        if user_id:
            identities = [item for item in identities if item.user_id == user_id]
        if channel_type:
            identities = [item for item in identities if item.channel_type == channel_type]
        return sorted(identities, key=lambda item: (item.tenant_id, item.channel_type, item.external_user_id))

    def upsert_identity(
        self,
        *,
        tenant_id: str,
        user_id: str,
        channel_type: str,
        external_user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> TenantUserIdentityDefinition:
        definition = TenantUserIdentityDefinition(
            tenant_id=tenant_id,
            user_id=user_id,
            channel_type=channel_type,
            external_user_id=external_user_id,
            metadata=dict(metadata or {}),
        )
        self.identities[(tenant_id, channel_type, external_user_id)] = definition
        return definition

    def delete_identity(
        self,
        *,
        tenant_id: str,
        channel_type: str,
        external_user_id: str,
    ) -> TenantUserIdentityDefinition:
        key = (tenant_id, channel_type, external_user_id)
        definition = self.identities.pop(key, None)
        if definition is None:
            raise KeyError(f"tenant identity not found: {tenant_id}/{channel_type}/{external_user_id}")
        return definition

    def find_user_by_identity(
        self,
        *,
        tenant_id: str,
        channel_type: str,
        external_user_id: str,
    ) -> TenantUserDefinition | None:
        identity = self.identities.get((tenant_id, channel_type, external_user_id))
        if identity is None:
            return None
        return self.get_user(identity.tenant_id, identity.user_id)

    @staticmethod
    def export_user_record(definition: TenantUserDefinition) -> dict[str, Any]:
        return {
            "tenant_id": definition.tenant_id,
            "user_id": definition.user_id,
            "name": definition.name,
            "role": definition.role,
            "status": definition.status,
            "metadata": dict(definition.metadata),
            "created_at": None,
            "updated_at": None,
        }

    @staticmethod
    def export_identity_record(definition: TenantUserIdentityDefinition) -> dict[str, Any]:
        return {
            "tenant_id": definition.tenant_id,
            "user_id": definition.user_id,
            "channel_type": definition.channel_type,
            "external_user_id": definition.external_user_id,
            "metadata": dict(definition.metadata),
            "created_at": None,
            "updated_at": None,
        }


class InMemoryAgentRepository:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.agents: dict[tuple[str, str], AgentDefinition] = {}
        self.versions: dict[tuple[str, str], list[dict[str, Any]]] = {}

    def list_agents(self, tenant_id: str) -> list[AgentDefinition]:
        return sorted(
            [agent for agent in self.agents.values() if agent.tenant_id == tenant_id],
            key=lambda item: item.agent_id,
        )

    def get_agent(self, tenant_id: str, agent_id: str) -> AgentDefinition | None:
        return self.agents.get((tenant_id, agent_id))

    def create_agent(
        self,
        tenant_id: str,
        agent_id: str,
        name: str,
        model: str = "",
        model_config_id: str = "",
        system_prompt: str = "",
        metadata: dict[str, Any] | None = None,
        tools: tuple[str, ...] | list[str] | None = None,
        skills: tuple[str, ...] | list[str] | None = None,
        knowledge_enabled: bool = False,
        mcp_servers: dict[str, Any] | None = None,
    ) -> AgentDefinition:
        key = (tenant_id, agent_id)
        if key in self.agents:
            raise ValueError(f"agent already exists: {agent_id}")
        definition = AgentDefinition(
            tenant_id=tenant_id,
            agent_id=agent_id,
            name=name,
            model=model,
            model_config_id=model_config_id,
            system_prompt=system_prompt,
            metadata=dict(metadata or {}),
            tools=tuple(tools or ()),
            skills=tuple(skills or ()),
            knowledge_enabled=knowledge_enabled,
            mcp_servers=dict(mcp_servers or {}),
        )
        self.agents[key] = definition
        self.versions[key] = [self._version_record(definition)]
        return definition

    def update_agent(self, tenant_id: str, agent_id: str, **kwargs: Any) -> AgentDefinition:
        current = self.agents.get((tenant_id, agent_id))
        if current is None:
            raise KeyError(f"agent not found: {agent_id}")
        data = asdict(current)
        data.update({key: value for key, value in kwargs.items() if value is not None})
        data["version"] = current.version + 1
        definition = AgentDefinition(**data)
        self.agents[(tenant_id, agent_id)] = definition
        self.versions.setdefault((tenant_id, agent_id), []).append(self._version_record(definition))
        return definition

    def delete_agent(self, tenant_id: str, agent_id: str) -> AgentDefinition:
        definition = self.agents.pop((tenant_id, agent_id), None)
        if definition is None:
            raise KeyError(f"agent not found: {agent_id}")
        return definition

    def get_workspace_path(self, tenant_id: str, agent_id: str) -> Path:
        return self.workspace_root / "workspaces" / tenant_id / agent_id

    def export_record_by_id(self, tenant_id: str, agent_id: str) -> dict[str, Any]:
        definition = self.get_agent(tenant_id, agent_id)
        if definition is None:
            raise KeyError(f"agent not found: {agent_id}")
        return self.export_record(definition)

    def export_record(self, definition: AgentDefinition) -> dict[str, Any]:
        return {
            "tenant_id": definition.tenant_id,
            "agent_id": definition.agent_id,
            "name": definition.name,
            "version": definition.version,
            "model": definition.model,
            "model_config_id": definition.model_config_id,
            "system_prompt": definition.system_prompt,
            "metadata": dict(definition.metadata),
            "tools": list(definition.tools),
            "skills": list(definition.skills),
            "knowledge_enabled": definition.knowledge_enabled,
            "mcp_servers": dict(definition.mcp_servers),
            "versions": list(self.versions.get((definition.tenant_id, definition.agent_id), [])),
            "created_at": None,
            "updated_at": None,
            "workspace_path": str(self.get_workspace_path(definition.tenant_id, definition.agent_id)),
        }

    @staticmethod
    def _version_record(definition: AgentDefinition) -> dict[str, Any]:
        return {
            "version": definition.version,
            "name": definition.name,
            "model": definition.model,
            "model_config_id": definition.model_config_id,
            "system_prompt": definition.system_prompt,
            "metadata": dict(definition.metadata),
            "tools": list(definition.tools),
            "skills": list(definition.skills),
            "knowledge_enabled": definition.knowledge_enabled,
            "mcp_servers": dict(definition.mcp_servers),
            "updated_at": int(time.time()),
        }


class InMemoryTenantMcpServerRepository:
    def __init__(self) -> None:
        self.servers: dict[tuple[str, str], TenantMcpServerDefinition] = {}

    def list_servers(self, tenant_id: str) -> list[TenantMcpServerDefinition]:
        return sorted(
            [server for server in self.servers.values() if server.tenant_id == tenant_id],
            key=lambda item: item.name,
        )

    def get_server(self, tenant_id: str, name: str) -> TenantMcpServerDefinition | None:
        return self.servers.get((tenant_id, name))

    def upsert_server(
        self,
        *,
        tenant_id: str,
        name: str,
        command: str,
        args: list[str] | tuple[str, ...] | None = None,
        env: dict[str, str] | None = None,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> TenantMcpServerDefinition:
        definition = TenantMcpServerDefinition(
            tenant_id=tenant_id,
            name=name,
            command=command,
            args=tuple(args or ()),
            env=dict(env or {}),
            enabled=enabled,
            metadata=dict(metadata or {}),
        )
        self.servers[(tenant_id, name)] = definition
        return definition

    def delete_server(self, tenant_id: str, name: str) -> TenantMcpServerDefinition:
        definition = self.servers.pop((tenant_id, name), None)
        if definition is None:
            raise KeyError(f"mcp server not found: {name}")
        return definition


class InMemoryBindingRepository:
    def __init__(self) -> None:
        self.bindings: dict[tuple[str, str], ChannelBindingDefinition] = {}

    def list_bindings(
        self,
        *,
        tenant_id: str = "",
        channel_type: str = "",
        channel_config_id: str = "",
    ) -> list[ChannelBindingDefinition]:
        bindings = list(self.bindings.values())
        if tenant_id:
            bindings = [item for item in bindings if item.tenant_id == tenant_id]
        if channel_type:
            bindings = [item for item in bindings if item.channel_type == channel_type]
        if channel_config_id:
            bindings = [item for item in bindings if item.channel_config_id == channel_config_id]
        return sorted(bindings, key=lambda item: (item.tenant_id, item.binding_id))

    def get_binding(self, *, tenant_id: str = "", binding_id: str) -> ChannelBindingDefinition | None:
        if tenant_id:
            return self.bindings.get((tenant_id, binding_id))
        matches = [item for key, item in self.bindings.items() if key[1] == binding_id]
        return matches[0] if matches else None

    def create_binding(
        self,
        *,
        tenant_id: str,
        binding_id: str,
        name: str,
        channel_type: str,
        agent_id: str,
        channel_config_id: str = "",
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> ChannelBindingDefinition:
        key = (tenant_id, binding_id)
        if key in self.bindings:
            raise ValueError(f"binding already exists: {binding_id}")
        definition = ChannelBindingDefinition(
            tenant_id=tenant_id,
            binding_id=binding_id,
            name=name,
            channel_type=channel_type,
            agent_id=agent_id,
            channel_config_id=channel_config_id,
            enabled=enabled,
            metadata=dict(metadata or {}),
        )
        self.bindings[key] = definition
        return definition

    def update_binding(
        self,
        *,
        binding_id: str,
        tenant_id: str = "",
        name: str | None = None,
        channel_type: str | None = None,
        channel_config_id: str | None = None,
        agent_id: str | None = None,
        enabled: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChannelBindingDefinition:
        current = self.get_binding(tenant_id=tenant_id, binding_id=binding_id)
        if current is None:
            raise KeyError(f"binding not found: {binding_id}")
        definition = ChannelBindingDefinition(
            tenant_id=current.tenant_id,
            binding_id=current.binding_id,
            name=current.name if name is None else name,
            channel_type=current.channel_type if channel_type is None else channel_type,
            agent_id=current.agent_id if agent_id is None else agent_id,
            channel_config_id=current.channel_config_id if channel_config_id is None else channel_config_id,
            version=current.version + 1,
            enabled=current.enabled if enabled is None else enabled,
            metadata=dict(current.metadata if metadata is None else metadata),
        )
        self.bindings[(definition.tenant_id, definition.binding_id)] = definition
        return definition

    def delete_binding(self, *, binding_id: str, tenant_id: str = "") -> ChannelBindingDefinition:
        current = self.get_binding(tenant_id=tenant_id, binding_id=binding_id)
        if current is None:
            raise KeyError(f"binding not found: {binding_id}")
        return self.bindings.pop((current.tenant_id, current.binding_id))

    def export_record(self, definition: ChannelBindingDefinition) -> dict[str, Any]:
        return {
            "tenant_id": definition.tenant_id,
            "binding_id": definition.binding_id,
            "name": definition.name,
            "channel_type": definition.channel_type,
            "channel_config_id": definition.channel_config_id,
            "agent_id": definition.agent_id,
            "version": definition.version,
            "enabled": definition.enabled,
            "metadata": dict(definition.metadata),
            "created_at": None,
            "updated_at": None,
        }


class EmptyPlatformUserService:
    @staticmethod
    def list_users(*, role: str = "", status: str = "") -> list[Any]:
        return []

    @staticmethod
    def has_platform_admin() -> bool:
        return False

    @staticmethod
    def resolve_user(user_id: str) -> Any:
        raise KeyError(user_id)


class InMemoryPricingRepository:
    def __init__(self) -> None:
        self.records: dict[str, PricingDefinition] = {}

    def list_pricing(self) -> list[PricingDefinition]:
        return sorted(self.records.values(), key=lambda item: item.model)

    def get_pricing(self, model: str) -> PricingDefinition | None:
        return self.records.get(model)

    def upsert_pricing(
        self,
        *,
        model: str,
        input_price_per_million: float,
        output_price_per_million: float,
        currency: str = "CNY",
        metadata: dict[str, Any] | None = None,
    ) -> PricingDefinition:
        definition = PricingDefinition(
            model=model,
            input_price_per_million=float(input_price_per_million),
            output_price_per_million=float(output_price_per_million),
            currency=currency,
            metadata=dict(metadata or {}),
        )
        self.records[model] = definition
        return definition

    @staticmethod
    def export_record(definition: PricingDefinition) -> dict[str, Any]:
        return asdict(definition)


class InMemoryUsageRepository:
    def __init__(self) -> None:
        self.records: list[UsageRecord] = []

    def append_record(self, record: UsageRecord) -> UsageRecord:
        self.records.append(record)
        return record

    def list_records(
        self,
        *,
        tenant_id: str = "",
        agent_id: str = "",
        day: str = "",
        start: str = "",
        end: str = "",
        model: str = "",
        request_id: str = "",
        limit: int = 100,
    ) -> list[UsageRecord]:
        records = list(self.records)
        if tenant_id:
            records = [record for record in records if record.tenant_id == tenant_id]
        if agent_id:
            records = [record for record in records if record.agent_id == agent_id]
        if day:
            records = [record for record in records if record.created_at.startswith(day)]
        if start:
            records = [record for record in records if record.created_at >= start]
        if end:
            records = [record for record in records if record.created_at < end]
        if model:
            records = [record for record in records if record.model == model]
        if request_id:
            records = [record for record in records if record.request_id == request_id]
        return sorted(records, key=lambda item: item.created_at, reverse=True)[: max(1, int(limit))]

    def summarize(
        self,
        *,
        tenant_id: str = "",
        agent_id: str = "",
        day: str = "",
        start: str = "",
        end: str = "",
        model: str = "",
    ) -> dict[str, Any]:
        records = self.list_records(
            tenant_id=tenant_id,
            agent_id=agent_id,
            day=day,
            start=start,
            end=end,
            model=model,
            limit=10_000,
        )
        return self._summarize_records(records)

    def analytics(
        self,
        *,
        tenant_id: str = "",
        agent_id: str = "",
        bucket: str = "day",
        start: str = "",
        end: str = "",
        model: str = "",
        limit: int = 10,
    ) -> dict[str, Any]:
        records = self.list_records(
            tenant_id=tenant_id,
            agent_id=agent_id,
            start=start,
            end=end,
            model=model,
            limit=10_000,
        )
        return {
            "summary": self._summarize_records(records),
            "time_series": self._group_records(records, self._bucket_key(bucket)),
            "agents": self._group_records(records, lambda record: record.agent_id, limit=limit),
            "models": self._group_records(records, lambda record: record.model or "unknown", limit=limit),
            "tools": self._metadata_counts(records, "tool_names", limit=limit),
            "mcp_tools": self._metadata_counts(records, "tool_names", prefix="mcp_", limit=limit),
            "skills": self._metadata_counts(records, "skill_names", limit=limit),
        }

    @staticmethod
    def _summarize_records(records: list[UsageRecord]) -> dict[str, Any]:
        return {
            "request_count": sum(record.request_count for record in records),
            "prompt_tokens": sum(record.prompt_tokens for record in records),
            "completion_tokens": sum(record.completion_tokens for record in records),
            "total_tokens": sum(record.total_tokens for record in records),
            "provider_request_count": sum(
                record.request_count for record in records if record.token_source == "provider"
            ),
            "estimated_request_count": sum(
                record.request_count for record in records if record.token_source != "provider"
            ),
            "tool_call_count": sum(record.tool_call_count for record in records),
            "mcp_call_count": sum(record.mcp_call_count for record in records),
            "tool_error_count": sum(record.tool_error_count for record in records),
            "tool_execution_time_ms": sum(record.tool_execution_time_ms for record in records),
            "estimated_cost": round(sum(record.estimated_cost for record in records), 6),
        }

    @classmethod
    def _group_records(
        cls,
        records: list[UsageRecord],
        key_func,
        *,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        groups: dict[str, list[UsageRecord]] = {}
        for record in records:
            key = str(key_func(record) or "unknown")
            groups.setdefault(key, []).append(record)
        items = []
        for key, grouped_records in groups.items():
            item = cls._summarize_records(grouped_records)
            item["key"] = key
            items.append(item)
        items.sort(key=lambda item: (-int(item["total_tokens"]), -int(item["request_count"]), str(item["key"])))
        if limit is None:
            return sorted(items, key=lambda item: str(item["key"]))
        return items[: max(1, int(limit))]

    @staticmethod
    def _metadata_counts(
        records: list[UsageRecord],
        metadata_key: str,
        *,
        prefix: str = "",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for record in records:
            values = dict((record.metadata or {}).get(metadata_key, {}) or {})
            for key, value in values.items():
                name = str(key or "").strip()
                if not name or (prefix and not name.startswith(prefix)):
                    continue
                counts[name] = counts.get(name, 0) + int(value or 0)
        items = [{"key": key, "count": count} for key, count in counts.items()]
        items.sort(key=lambda item: (-item["count"], item["key"]))
        return items[: max(1, int(limit))]

    @staticmethod
    def _bucket_key(bucket: str):
        normalized = bucket if bucket in {"hour", "day", "week", "month", "year"} else "day"
        if normalized == "hour":
            return lambda record: record.created_at[:13]
        if normalized == "day":
            return lambda record: record.created_at[:10]
        if normalized == "month":
            return lambda record: record.created_at[:7]
        if normalized == "year":
            return lambda record: record.created_at[:4]
        return lambda record: record.created_at[:10]

    @staticmethod
    def export_record(definition: UsageRecord) -> dict[str, Any]:
        return asdict(definition)


class InMemoryQuotaRepository:
    def __init__(self) -> None:
        self.records: dict[tuple[str, str, str], QuotaDefinition] = {}

    def list_quotas(
        self,
        *,
        scope_type: str = "",
        tenant_id: str = "",
        agent_id: str = "",
    ) -> list[QuotaDefinition]:
        quotas = list(self.records.values())
        if scope_type:
            quotas = [quota for quota in quotas if quota.scope_type == scope_type]
        if tenant_id:
            quotas = [quota for quota in quotas if quota.tenant_id == tenant_id]
        if agent_id:
            quotas = [quota for quota in quotas if quota.agent_id == agent_id]
        return sorted(quotas, key=lambda item: (item.scope_type, item.tenant_id, item.agent_id))

    def get_quota(self, *, scope_type: str, tenant_id: str, agent_id: str = "") -> QuotaDefinition | None:
        return self.records.get((scope_type, tenant_id, agent_id))

    def upsert_quota(
        self,
        *,
        scope_type: str,
        tenant_id: str,
        agent_id: str = "",
        max_requests_per_day: int = 0,
        max_tokens_per_day: int = 0,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> QuotaDefinition:
        definition = QuotaDefinition(
            scope_type=scope_type,
            tenant_id=tenant_id,
            agent_id=agent_id,
            max_requests_per_day=int(max_requests_per_day),
            max_tokens_per_day=int(max_tokens_per_day),
            enabled=bool(enabled),
            metadata=dict(metadata or {}),
        )
        self.records[(scope_type, tenant_id, agent_id)] = definition
        return definition

    @staticmethod
    def export_record(definition: QuotaDefinition) -> dict[str, Any]:
        return asdict(definition)


class InMemoryJobRepository:
    STATUSES = ("pending", "running", "completed", "failed")

    def __init__(self) -> None:
        self.records: dict[str, JobDefinition] = {}

    def create_job(
        self,
        *,
        job_id: str,
        job_type: str,
        tenant_id: str,
        agent_id: str = "",
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> JobDefinition:
        now = self._now()
        definition = JobDefinition(
            job_id=job_id,
            job_type=job_type,
            tenant_id=tenant_id,
            agent_id=agent_id,
            status="pending",
            payload=dict(payload or {}),
            result={},
            attempts=0,
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )
        self.records[job_id] = definition
        return definition

    def get_job(self, job_id: str) -> JobDefinition | None:
        return self.records.get(job_id)

    def list_jobs(
        self,
        *,
        status: str = "",
        tenant_id: str = "",
        agent_id: str = "",
        limit: int = 100,
    ) -> list[JobDefinition]:
        jobs = list(self.records.values())
        if status:
            jobs = [job for job in jobs if job.status == status]
        if tenant_id:
            jobs = [job for job in jobs if job.tenant_id == tenant_id]
        if agent_id:
            jobs = [job for job in jobs if job.agent_id == agent_id]
        return sorted(jobs, key=lambda item: item.created_at, reverse=True)[: max(1, int(limit))]

    def claim_next_job(self, *, job_type: str = "") -> JobDefinition | None:
        candidates = [
            job
            for job in self.records.values()
            if job.status == "pending" and (not job_type or job.job_type == job_type)
        ]
        if not candidates:
            return None
        job = sorted(candidates, key=lambda item: item.created_at)[0]
        return self._replace(job, status="running", attempts=job.attempts + 1, started_at=self._now())

    def complete_job(self, job_id: str, result: dict[str, Any] | None = None) -> JobDefinition:
        job = self.records.get(job_id)
        if job is None or job.status != "running":
            raise KeyError(f"running job not found: {job_id}")
        return self._replace(job, status="completed", result=dict(result or {}), completed_at=self._now())

    def fail_job(self, job_id: str, error_message: str) -> JobDefinition:
        job = self.records.get(job_id)
        if job is None or job.status != "running":
            raise KeyError(f"running job not found: {job_id}")
        return self._replace(job, status="failed", error_message=error_message, completed_at=self._now())

    @staticmethod
    def export_record(definition: JobDefinition) -> dict[str, Any]:
        return asdict(definition)

    def _replace(self, job: JobDefinition, **kwargs: Any) -> JobDefinition:
        data = asdict(job)
        data.update(kwargs)
        data["updated_at"] = self._now()
        definition = JobDefinition(**data)
        self.records[job.job_id] = definition
        return definition

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")


class InMemoryAuditRepository:
    def __init__(self) -> None:
        self.records: list[AuditLogRecord] = []

    def append_record(self, record: AuditLogRecord) -> AuditLogRecord:
        self.records.append(record)
        return record

    def list_records(
        self,
        *,
        action: str = "",
        resource_type: str = "",
        tenant_id: str = "",
        agent_id: str = "",
        limit: int = 100,
    ) -> list[AuditLogRecord]:
        records = list(self.records)
        if action:
            records = [record for record in records if record.action == action]
        if resource_type:
            records = [record for record in records if record.resource_type == resource_type]
        if tenant_id:
            records = [record for record in records if record.tenant_id == tenant_id]
        if agent_id:
            records = [record for record in records if record.agent_id == agent_id]
        return sorted(records, key=lambda item: item.created_at, reverse=True)[: max(1, int(limit))]

    @staticmethod
    def export_record(definition: AuditLogRecord) -> dict[str, Any]:
        return asdict(definition)
