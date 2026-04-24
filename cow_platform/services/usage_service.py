from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any

from agent.protocol.agent import Agent as ProtocolAgent

from cow_platform.domain.models import UsageRecord
from cow_platform.repositories.usage_repository import UsageRepository
from cow_platform.services.pricing_service import PricingService


class UsageService:
    """Usage ledger service backed by PostgreSQL."""

    def __init__(
        self,
        repository: UsageRepository | None = None,
        pricing_service: PricingService | None = None,
    ):
        self.repository = repository or UsageRepository()
        self.pricing_service = pricing_service or PricingService()

    @staticmethod
    def estimate_text_tokens(text: str) -> int:
        return ProtocolAgent._estimate_text_tokens(text or "")

    def record_chat_usage(
        self,
        *,
        request_id: str,
        tenant_id: str,
        agent_id: str,
        binding_id: str = "",
        session_id: str = "",
        channel_type: str = "",
        model: str = "",
        prompt_text: str = "",
        completion_text: str = "",
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        token_source: str | None = None,
        tool_call_count: int = 0,
        mcp_call_count: int = 0,
        tool_error_count: int = 0,
        tool_execution_time_ms: int = 0,
        created_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_prompt_tokens = int(prompt_tokens if prompt_tokens is not None else self.estimate_text_tokens(prompt_text))
        resolved_completion_tokens = int(
            completion_tokens if completion_tokens is not None else self.estimate_text_tokens(completion_text)
        )
        total_tokens = resolved_prompt_tokens + resolved_completion_tokens
        resolved_token_source = token_source or (
            "provider" if prompt_tokens is not None or completion_tokens is not None else "estimated"
        )
        pricing = self.pricing_service.resolve_pricing(model or "unknown")
        estimated_cost = (
            (resolved_prompt_tokens / 1_000_000.0) * float(pricing.input_price_per_million)
            + (resolved_completion_tokens / 1_000_000.0) * float(pricing.output_price_per_million)
        )

        record = UsageRecord(
            event_id=f"evt_{uuid.uuid4().hex}",
            request_id=request_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            binding_id=binding_id,
            session_id=session_id,
            channel_type=channel_type,
            model=model,
            prompt_tokens=resolved_prompt_tokens,
            completion_tokens=resolved_completion_tokens,
            total_tokens=total_tokens,
            token_source=resolved_token_source,
            tool_call_count=max(0, int(tool_call_count)),
            mcp_call_count=max(0, int(mcp_call_count)),
            tool_error_count=max(0, int(tool_error_count)),
            tool_execution_time_ms=max(0, int(tool_execution_time_ms)),
            estimated_cost=round(estimated_cost, 6),
            created_at=created_at or datetime.now().isoformat(timespec="seconds"),
            metadata=metadata or {},
        )
        self.repository.append_record(record)
        return self.serialize_usage(record)

    def list_usage_records(
        self,
        *,
        tenant_id: str = "",
        agent_id: str = "",
        day: str = "",
        request_id: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return [
            self.serialize_usage(item)
            for item in self.repository.list_records(
                tenant_id=tenant_id,
                agent_id=agent_id,
                day=day,
                request_id=request_id,
                limit=limit,
            )
        ]

    def summarize_usage(
        self,
        *,
        tenant_id: str = "",
        agent_id: str = "",
        day: str = "",
    ) -> dict[str, Any]:
        summary = self.repository.summarize(tenant_id=tenant_id, agent_id=agent_id, day=day)
        summary["tenant_id"] = tenant_id
        summary["agent_id"] = agent_id
        summary["day"] = day
        return summary

    def serialize_usage(self, definition: UsageRecord) -> dict[str, Any]:
        return self.repository.export_record(definition)
