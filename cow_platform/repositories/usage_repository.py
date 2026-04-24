from __future__ import annotations

from dataclasses import asdict
from typing import Any

from cow_platform.db import connect, jsonb
from cow_platform.domain.models import UsageRecord


class PostgresUsageRepository:
    """PostgreSQL-backed usage ledger."""

    def append_record(self, record: UsageRecord) -> UsageRecord:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO platform_usage_records
                    (event_id, request_id, tenant_id, agent_id, binding_id, session_id,
                     channel_type, model, prompt_tokens, completion_tokens, total_tokens,
                     token_source, request_count, tool_call_count, mcp_call_count,
                     tool_error_count, tool_execution_time_ms, estimated_cost,
                     created_at, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s)
                """,
                (
                    record.event_id,
                    record.request_id,
                    record.tenant_id,
                    record.agent_id,
                    record.binding_id,
                    record.session_id,
                    record.channel_type,
                    record.model,
                    int(record.prompt_tokens),
                    int(record.completion_tokens),
                    int(record.total_tokens),
                    record.token_source,
                    int(record.request_count),
                    int(record.tool_call_count),
                    int(record.mcp_call_count),
                    int(record.tool_error_count),
                    int(record.tool_execution_time_ms),
                    float(record.estimated_cost),
                    record.created_at,
                    jsonb(record.metadata or {}),
                ),
            )
            conn.commit()
        return record

    def list_records(
        self,
        *,
        tenant_id: str = "",
        agent_id: str = "",
        day: str = "",
        request_id: str = "",
        limit: int = 100,
    ) -> list[UsageRecord]:
        conditions: list[str] = []
        params: list[Any] = []
        if tenant_id:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
        if agent_id:
            conditions.append("agent_id = %s")
            params.append(agent_id)
        if day:
            conditions.append("created_at LIKE %s")
            params.append(f"{day}%")
        if request_id:
            conditions.append("request_id = %s")
            params.append(request_id)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(max(1, int(limit)))
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM platform_usage_records
                {where}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                tuple(params),
            ).fetchall()
        return [self._to_definition(row) for row in rows]

    def summarize(
        self,
        *,
        tenant_id: str = "",
        agent_id: str = "",
        day: str = "",
    ) -> dict[str, Any]:
        conditions: list[str] = []
        params: list[Any] = []
        if tenant_id:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
        if agent_id:
            conditions.append("agent_id = %s")
            params.append(agent_id)
        if day:
            conditions.append("created_at LIKE %s")
            params.append(f"{day}%")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with connect() as conn:
            row = conn.execute(
                f"""
                SELECT
                    COALESCE(SUM(request_count), 0) AS request_count,
                    COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens,
                    COALESCE(SUM(CASE WHEN token_source = 'provider' THEN request_count ELSE 0 END), 0)
                        AS provider_request_count,
                    COALESCE(SUM(CASE WHEN token_source = 'provider' THEN 0 ELSE request_count END), 0)
                        AS estimated_request_count,
                    COALESCE(SUM(tool_call_count), 0) AS tool_call_count,
                    COALESCE(SUM(mcp_call_count), 0) AS mcp_call_count,
                    COALESCE(SUM(tool_error_count), 0) AS tool_error_count,
                    COALESCE(SUM(tool_execution_time_ms), 0) AS tool_execution_time_ms,
                    COALESCE(SUM(estimated_cost), 0) AS estimated_cost
                FROM platform_usage_records
                {where}
                """,
                tuple(params),
            ).fetchone()
        return {
            "request_count": int(row["request_count"]),
            "prompt_tokens": int(row["prompt_tokens"]),
            "completion_tokens": int(row["completion_tokens"]),
            "total_tokens": int(row["total_tokens"]),
            "provider_request_count": int(row["provider_request_count"]),
            "estimated_request_count": int(row["estimated_request_count"]),
            "tool_call_count": int(row["tool_call_count"]),
            "mcp_call_count": int(row["mcp_call_count"]),
            "tool_error_count": int(row["tool_error_count"]),
            "tool_execution_time_ms": int(row["tool_execution_time_ms"]),
            "estimated_cost": round(float(row["estimated_cost"]), 6),
        }

    @staticmethod
    def export_record(definition: UsageRecord) -> dict[str, Any]:
        return asdict(definition)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> UsageRecord:
        return UsageRecord(
            event_id=record["event_id"],
            request_id=record["request_id"],
            tenant_id=record["tenant_id"],
            agent_id=record["agent_id"],
            binding_id=record.get("binding_id", ""),
            session_id=record.get("session_id", ""),
            channel_type=record.get("channel_type", ""),
            model=record.get("model", ""),
            prompt_tokens=int(record.get("prompt_tokens", 0)),
            completion_tokens=int(record.get("completion_tokens", 0)),
            total_tokens=int(record.get("total_tokens", 0)),
            token_source=record.get("token_source", "estimated"),
            request_count=int(record.get("request_count", 1)),
            tool_call_count=int(record.get("tool_call_count", 0)),
            mcp_call_count=int(record.get("mcp_call_count", 0)),
            tool_error_count=int(record.get("tool_error_count", 0)),
            tool_execution_time_ms=int(record.get("tool_execution_time_ms", 0)),
            estimated_cost=float(record.get("estimated_cost", 0.0)),
            created_at=record["created_at"],
            metadata=record.get("metadata", {}) or {},
        )


UsageRepository = PostgresUsageRepository
