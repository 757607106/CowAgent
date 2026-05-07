from __future__ import annotations

import uuid
from typing import Any


class AgentGovernanceService:
    """Quota and usage facade used by the CoreAgent bridge."""

    def __init__(self, *, pricing_service=None, usage_service=None, quota_service=None):
        from cow_platform.services.pricing_service import PricingService
        from cow_platform.services.quota_service import QuotaService
        from cow_platform.services.usage_service import UsageService

        self.pricing_service = pricing_service or PricingService()
        self.usage_service = usage_service or UsageService(pricing_service=self.pricing_service)
        self.quota_service = quota_service or QuotaService(usage_service=self.usage_service)

    def check_request_allowed(self, *, runtime_context, query: str) -> dict:
        return self.quota_service.check_request_allowed(
            tenant_id=runtime_context.tenant_id,
            agent_id=runtime_context.agent_id,
            prompt_tokens=self.usage_service.estimate_text_tokens(query),
        )

    def record_agent_usage(
        self,
        *,
        resolved_runtime,
        request_id: str,
        query: str,
        completion_text: str,
        model: str,
        channel_type: str,
        status: str,
        agent: Any = None,
        event_handler: Any = None,
    ) -> None:
        runtime_context = resolved_runtime.runtime_context
        provider_usage = self.normalize_provider_usage(getattr(agent, "last_usage", None) if agent else None)
        usage_metrics = event_handler.get_usage_metrics() if event_handler else {}
        skill_names = {
            str(name): 1
            for name in getattr(resolved_runtime.agent_definition, "skills", ())
            if str(name or "").strip()
        }
        metadata = {
            "status": status,
            "tool_names": usage_metrics.get("tool_names", {}),
        }
        if skill_names:
            metadata["skill_names"] = skill_names
        if provider_usage:
            metadata["provider_usage"] = provider_usage
        self.usage_service.record_chat_usage(
            request_id=request_id or f"req_{uuid.uuid4().hex}",
            tenant_id=runtime_context.tenant_id,
            agent_id=runtime_context.agent_id,
            binding_id=str(runtime_context.metadata.get("binding_id", "") or ""),
            session_id=runtime_context.session_id,
            channel_type=channel_type,
            model=model,
            prompt_text=query,
            completion_text=completion_text,
            prompt_tokens=provider_usage.get("prompt_tokens"),
            completion_tokens=provider_usage.get("completion_tokens"),
            token_source="provider" if provider_usage else "estimated",
            tool_call_count=int(usage_metrics.get("tool_call_count", 0)),
            mcp_call_count=int(usage_metrics.get("mcp_call_count", 0)),
            tool_error_count=int(usage_metrics.get("tool_error_count", 0)),
            tool_execution_time_ms=int(usage_metrics.get("tool_execution_time_ms", 0)),
            metadata=metadata,
        )

    @staticmethod
    def normalize_provider_usage(raw_usage: Any) -> dict[str, int]:
        if not isinstance(raw_usage, dict) or not raw_usage:
            return {}

        def _read_int(*keys: str) -> int | None:
            for key in keys:
                if key not in raw_usage:
                    continue
                value = raw_usage.get(key)
                if value in (None, ""):
                    continue
                try:
                    return max(0, int(value))
                except (TypeError, ValueError):
                    continue
            return None

        prompt_tokens = _read_int("prompt_tokens", "input_tokens", "promptTokenCount")
        completion_tokens = _read_int("completion_tokens", "output_tokens", "candidatesTokenCount")
        total_tokens = _read_int("total_tokens", "totalTokenCount")

        if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
            total_tokens = prompt_tokens + completion_tokens
        if prompt_tokens is None and total_tokens is not None and completion_tokens is not None:
            prompt_tokens = max(0, total_tokens - completion_tokens)
        if completion_tokens is None and total_tokens is not None and prompt_tokens is not None:
            completion_tokens = max(0, total_tokens - prompt_tokens)

        normalized = {}
        if prompt_tokens is not None:
            normalized["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            normalized["completion_tokens"] = completion_tokens
        if total_tokens is not None:
            normalized["total_tokens"] = total_tokens
        return normalized
