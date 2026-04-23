from __future__ import annotations

from datetime import datetime
from typing import Any

from cow_platform.domain.models import QuotaDefinition
from cow_platform.repositories.quota_repository import FileQuotaRepository
from cow_platform.services.usage_service import UsageService


class QuotaService:
    """当前阶段使用的配额服务。"""

    def __init__(
        self,
        repository: FileQuotaRepository | None = None,
        usage_service: UsageService | None = None,
    ):
        self.repository = repository or FileQuotaRepository()
        self.usage_service = usage_service or UsageService()

    def list_quotas(self, *, scope_type: str = "", tenant_id: str = "", agent_id: str = "") -> list[QuotaDefinition]:
        return self.repository.list_quotas(scope_type=scope_type, tenant_id=tenant_id, agent_id=agent_id)

    def upsert_quota(
        self,
        *,
        scope_type: str,
        tenant_id: str,
        agent_id: str = "",
        max_requests_per_day: int = 0,
        max_tokens_per_day: int = 0,
        enabled: bool = True,
    ) -> dict[str, Any]:
        definition = self.repository.upsert_quota(
            scope_type=scope_type,
            tenant_id=tenant_id,
            agent_id=agent_id,
            max_requests_per_day=max_requests_per_day,
            max_tokens_per_day=max_tokens_per_day,
            enabled=enabled,
        )
        return self.serialize_quota(definition)

    def list_quota_records(self, *, scope_type: str = "", tenant_id: str = "", agent_id: str = "") -> list[dict[str, Any]]:
        return [
            self.serialize_quota(item)
            for item in self.list_quotas(scope_type=scope_type, tenant_id=tenant_id, agent_id=agent_id)
        ]

    def check_request_allowed(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        prompt_tokens: int,
        day: str | None = None,
    ) -> dict[str, Any]:
        resolved_day = day or datetime.now().strftime("%Y-%m-%d")
        quota_chain = [
            self.repository.get_quota(scope_type="tenant", tenant_id=tenant_id),
            self.repository.get_quota(scope_type="agent", tenant_id=tenant_id, agent_id=agent_id),
        ]
        for quota in quota_chain:
            if quota is None or not quota.enabled:
                continue

            if quota.scope_type == "tenant":
                summary = self.usage_service.summarize_usage(tenant_id=tenant_id, day=resolved_day)
                scope_label = f"tenant:{tenant_id}"
            else:
                summary = self.usage_service.summarize_usage(tenant_id=tenant_id, agent_id=agent_id, day=resolved_day)
                scope_label = f"agent:{tenant_id}/{agent_id}"

            if quota.max_requests_per_day > 0 and summary["request_count"] + 1 > quota.max_requests_per_day:
                return {
                    "allowed": False,
                    "scope": scope_label,
                    "reason": "request_limit",
                    "message": f"已超过当日请求配额: {scope_label}",
                    "summary": summary,
                }

            if quota.max_tokens_per_day > 0 and summary["total_tokens"] + int(prompt_tokens) > quota.max_tokens_per_day:
                return {
                    "allowed": False,
                    "scope": scope_label,
                    "reason": "token_limit",
                    "message": f"已超过当日 Token 配额: {scope_label}",
                    "summary": summary,
                }

        return {
            "allowed": True,
            "scope": "",
            "reason": "",
            "message": "",
            "summary": {},
        }

    def serialize_quota(self, definition: QuotaDefinition) -> dict[str, Any]:
        return self.repository.export_record(definition)
