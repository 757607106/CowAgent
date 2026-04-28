from __future__ import annotations

from datetime import datetime, timedelta
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
        bucket: str = "",
        day: str = "",
        start: str = "",
        end: str = "",
        model: str = "",
        request_id: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        start_at, end_at = self.resolve_time_range(
            bucket=self.normalize_bucket(bucket),
            start=start,
            end=end,
            with_default=bool(bucket),
        )
        return [
            self.serialize_usage(item)
            for item in self.repository.list_records(
                tenant_id=tenant_id,
                agent_id=agent_id,
                day=day,
                start=start_at,
                end=end_at,
                model=model,
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
        start: str = "",
        end: str = "",
        model: str = "",
    ) -> dict[str, Any]:
        start_at, end_at = self.resolve_time_range(bucket="day", start=start, end=end, with_default=False)
        summary = self.repository.summarize(
            tenant_id=tenant_id,
            agent_id=agent_id,
            day=day,
            start=start_at,
            end=end_at,
            model=model,
        )
        summary["tenant_id"] = tenant_id
        summary["agent_id"] = agent_id
        summary["day"] = day
        summary["start"] = start_at
        summary["end"] = end_at
        summary["model"] = model
        return summary

    def get_usage_analytics(
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
        resolved_bucket = self.normalize_bucket(bucket)
        start_at, end_at = self.resolve_time_range(bucket=resolved_bucket, start=start, end=end)
        analytics = self.repository.analytics(
            tenant_id=tenant_id,
            agent_id=agent_id,
            bucket=resolved_bucket,
            start=start_at,
            end=end_at,
            model=model,
            limit=limit,
        )
        analytics["tenant_id"] = tenant_id
        analytics["agent_id"] = agent_id
        analytics["bucket"] = resolved_bucket
        analytics["start"] = start_at
        analytics["end"] = end_at
        analytics["model"] = model
        return analytics

    def serialize_usage(self, definition: UsageRecord) -> dict[str, Any]:
        return self.repository.export_record(definition)

    @staticmethod
    def normalize_bucket(bucket: str) -> str:
        normalized = (bucket or "day").strip().lower()
        return normalized if normalized in {"hour", "day", "week", "month", "year"} else "day"

    @classmethod
    def resolve_time_range(
        cls,
        *,
        bucket: str,
        start: str = "",
        end: str = "",
        with_default: bool = True,
    ) -> tuple[str, str]:
        start_at = cls.normalize_time_boundary(start, is_end=False)
        end_at = cls.normalize_time_boundary(end, is_end=True)
        if start_at or end_at or not with_default:
            return start_at, end_at

        now = datetime.now().replace(microsecond=0)
        normalized_bucket = cls.normalize_bucket(bucket)
        if normalized_bucket == "hour":
            start_dt = now - timedelta(hours=24)
        elif normalized_bucket == "day":
            start_dt = now - timedelta(days=29)
        elif normalized_bucket == "week":
            start_dt = now - timedelta(weeks=12)
        elif normalized_bucket == "month":
            start_dt = cls._add_months(now.replace(day=1, hour=0, minute=0, second=0), -11)
        else:
            start_dt = now.replace(month=1, day=1, hour=0, minute=0, second=0)
            start_dt = start_dt.replace(year=start_dt.year - 4)
        return start_dt.isoformat(timespec="seconds"), (now + timedelta(seconds=1)).isoformat(timespec="seconds")

    @staticmethod
    def normalize_time_boundary(value: str, *, is_end: bool) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        normalized = text.replace(" ", "T")
        try:
            if len(normalized) == 4:
                dt = datetime.fromisoformat(f"{normalized}-01-01T00:00:00")
                if is_end:
                    dt = dt.replace(year=dt.year + 1)
                return dt.isoformat(timespec="seconds")
            if len(normalized) == 7:
                dt = datetime.fromisoformat(f"{normalized}-01T00:00:00")
                if is_end:
                    dt = UsageService._add_months(dt, 1)
                return dt.isoformat(timespec="seconds")
            if len(normalized) == 10:
                dt = datetime.fromisoformat(f"{normalized}T00:00:00")
                if is_end:
                    dt += timedelta(days=1)
                return dt.isoformat(timespec="seconds")
            if len(normalized) == 13:
                dt = datetime.fromisoformat(f"{normalized}:00:00")
                if is_end:
                    dt += timedelta(hours=1)
                return dt.isoformat(timespec="seconds")
            dt = datetime.fromisoformat(normalized)
            return dt.isoformat(timespec="seconds")
        except ValueError:
            return ""

    @staticmethod
    def _add_months(value: datetime, months: int) -> datetime:
        month_index = value.month - 1 + months
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        return value.replace(year=year, month=month)
