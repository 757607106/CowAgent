from __future__ import annotations

from typing import Any

from common.log import logger
from cow_platform.domain.models import ChannelBindingDefinition
from cow_platform.repositories.binding_repository import FileChannelBindingRepository
from cow_platform.services.agent_service import AgentService
from cow_platform.services.tenant_service import TenantService


class ChannelBindingService:
    """当前阶段使用的渠道绑定服务。"""

    def __init__(
        self,
        repository: FileChannelBindingRepository | None = None,
        tenant_service: TenantService | None = None,
        agent_service: AgentService | None = None,
    ):
        self.repository = repository or FileChannelBindingRepository()
        self.tenant_service = tenant_service or TenantService()
        self.agent_service = agent_service or AgentService()

    def list_bindings(
        self,
        *,
        tenant_id: str = "",
        channel_type: str = "",
    ) -> list[ChannelBindingDefinition]:
        return self.repository.list_bindings(tenant_id=tenant_id, channel_type=channel_type)

    def resolve_binding(
        self,
        *,
        binding_id: str,
        tenant_id: str = "",
    ) -> ChannelBindingDefinition:
        definition = self.repository.get_binding(tenant_id=tenant_id, binding_id=binding_id)
        if definition is None:
            raise KeyError(f"binding not found: {binding_id}")
        return definition

    def resolve_binding_for_channel(
        self,
        *,
        channel_type: str,
        external_app_id: str = "",
        external_chat_id: str = "",
        external_user_id: str = "",
    ) -> ChannelBindingDefinition | None:
        candidates: list[tuple[int, str, ChannelBindingDefinition]] = []
        for definition in self.list_bindings(channel_type=channel_type):
            if not definition.enabled:
                continue
            score = self._score_binding_metadata(
                definition,
                external_app_id=external_app_id,
                external_chat_id=external_chat_id,
                external_user_id=external_user_id,
            )
            if score < 0:
                continue
            candidates.append((score, f"{definition.tenant_id}:{definition.binding_id}", definition))

        if not candidates:
            return None

        candidates.sort(key=lambda item: (-item[0], item[1]))
        top_score = candidates[0][0]
        top_candidates = [item for item in candidates if item[0] == top_score]
        if len(top_candidates) > 1:
            logger.warning(
                "[BindingService] Ambiguous binding resolution for "
                f"channel_type={channel_type}, app={external_app_id}, chat={external_chat_id}, user={external_user_id}: "
                f"{[item[2].binding_id for item in top_candidates]}"
            )
            return None
        return candidates[0][2]

    def create_binding(
        self,
        *,
        tenant_id: str,
        binding_id: str,
        name: str,
        channel_type: str,
        agent_id: str,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.tenant_service.resolve_tenant(tenant_id)
        self.agent_service.resolve_agent(tenant_id=tenant_id, agent_id=agent_id)
        definition = self.repository.create_binding(
            tenant_id=tenant_id,
            binding_id=binding_id,
            name=name,
            channel_type=channel_type,
            agent_id=agent_id,
            enabled=enabled,
            metadata=metadata or {},
        )
        return self.serialize_binding(definition)

    def update_binding(
        self,
        binding_id: str,
        *,
        tenant_id: str = "",
        name: str | None = None,
        channel_type: str | None = None,
        agent_id: str | None = None,
        enabled: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing = self.resolve_binding(binding_id=binding_id, tenant_id=tenant_id)
        resolved_tenant_id = tenant_id or existing.tenant_id
        if agent_id is not None:
            self.agent_service.resolve_agent(tenant_id=resolved_tenant_id, agent_id=agent_id)
        definition = self.repository.update_binding(
            binding_id=binding_id,
            tenant_id=resolved_tenant_id,
            name=name,
            channel_type=channel_type,
            agent_id=agent_id,
            enabled=enabled,
            metadata=metadata,
        )
        return self.serialize_binding(definition)

    def serialize_binding(self, definition: ChannelBindingDefinition) -> dict[str, Any]:
        record = self.repository.export_record(definition)
        record["agent_workspace"] = str(
            self.agent_service.get_agent_workspace(definition.tenant_id, definition.agent_id)
        )
        return record

    def delete_binding(
        self,
        *,
        binding_id: str,
        tenant_id: str = "",
    ) -> dict[str, Any]:
        definition = self.repository.delete_binding(binding_id=binding_id, tenant_id=tenant_id)
        return self.serialize_binding(definition)

    def list_binding_records(
        self,
        *,
        tenant_id: str = "",
        channel_type: str = "",
    ) -> list[dict[str, Any]]:
        return [
            self.serialize_binding(item)
            for item in self.list_bindings(tenant_id=tenant_id, channel_type=channel_type)
        ]

    @staticmethod
    def _score_binding_metadata(
        definition: ChannelBindingDefinition,
        *,
        external_app_id: str = "",
        external_chat_id: str = "",
        external_user_id: str = "",
    ) -> int:
        metadata = dict(definition.metadata or {})
        expected_app_id = str(metadata.get("external_app_id", "") or "").strip()
        expected_chat_id = str(metadata.get("external_chat_id", "") or "").strip()
        expected_user_id = str(metadata.get("external_user_id", "") or "").strip()

        actual_app_id = str(external_app_id or "").strip()
        actual_chat_id = str(external_chat_id or "").strip()
        actual_user_id = str(external_user_id or "").strip()

        score = 1
        if expected_app_id:
            if actual_app_id != expected_app_id:
                return -1
            score += 8
        if expected_chat_id:
            if actual_chat_id != expected_chat_id:
                return -1
            score += 4
        if expected_user_id:
            if actual_user_id != expected_user_id:
                return -1
            score += 2
        return score
