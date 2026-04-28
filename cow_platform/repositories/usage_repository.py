from __future__ import annotations

from dataclasses import asdict
from typing import Any

from cow_platform.db import connect, jsonb
from cow_platform.domain.models import UsageRecord


class PostgresUsageRepository:
    """PostgreSQL-backed usage ledger."""

    SUMMARY_COLUMNS = """
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
    """

    BUCKET_EXPRESSIONS = {
        "hour": "SUBSTRING(created_at FROM 1 FOR 13)",
        "day": "SUBSTRING(created_at FROM 1 FOR 10)",
        "week": "TO_CHAR(DATE_TRUNC('week', created_at::timestamp), 'YYYY-MM-DD')",
        "month": "SUBSTRING(created_at FROM 1 FOR 7)",
        "year": "SUBSTRING(created_at FROM 1 FOR 4)",
    }

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
        start: str = "",
        end: str = "",
        model: str = "",
        request_id: str = "",
        limit: int = 100,
    ) -> list[UsageRecord]:
        conditions, params = self._build_conditions(
            tenant_id=tenant_id,
            agent_id=agent_id,
            day=day,
            start=start,
            end=end,
            model=model,
        )
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
        start: str = "",
        end: str = "",
        model: str = "",
    ) -> dict[str, Any]:
        conditions, params = self._build_conditions(
            tenant_id=tenant_id,
            agent_id=agent_id,
            day=day,
            start=start,
            end=end,
            model=model,
        )
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with connect() as conn:
            row = conn.execute(
                f"""
                SELECT
                    {self.SUMMARY_COLUMNS}
                FROM platform_usage_records
                {where}
                """,
                tuple(params),
            ).fetchone()
        return self._summary_from_row(row)

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
        bucket_expr = self.BUCKET_EXPRESSIONS.get(bucket, self.BUCKET_EXPRESSIONS["day"])
        conditions, params = self._build_conditions(
            tenant_id=tenant_id,
            agent_id=agent_id,
            start=start,
            end=end,
            model=model,
        )
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rank_limit = max(1, min(int(limit or 10), 50))
        with connect() as conn:
            summary = self._summary_from_row(
                conn.execute(
                    f"""
                    SELECT
                        {self.SUMMARY_COLUMNS}
                    FROM platform_usage_records
                    {where}
                    """,
                    tuple(params),
                ).fetchone()
            )
            time_rows = conn.execute(
                f"""
                SELECT
                    {bucket_expr} AS key,
                    {self.SUMMARY_COLUMNS}
                FROM platform_usage_records
                {where}
                GROUP BY key
                ORDER BY key ASC
                """,
                tuple(params),
            ).fetchall()
            agent_rows = self._query_dimension(conn, "agent_id", where, params, rank_limit)
            model_rows = self._query_dimension(conn, "COALESCE(NULLIF(model, ''), 'unknown')", where, params, rank_limit)
            tool_rows = self._query_metadata_counts(conn, "tool_names", where, params, rank_limit)
            mcp_rows = self._query_metadata_counts(conn, "tool_names", where, params, rank_limit, prefix="mcp_")
            skill_rows = self._query_metadata_counts(conn, "skill_names", where, params, rank_limit)

        return {
            "summary": summary,
            "time_series": [self._dimension_from_row(row) for row in time_rows],
            "agents": [self._dimension_from_row(row) for row in agent_rows],
            "models": [self._dimension_from_row(row) for row in model_rows],
            "tools": [self._count_from_row(row) for row in tool_rows],
            "mcp_tools": [self._count_from_row(row) for row in mcp_rows],
            "skills": [self._count_from_row(row) for row in skill_rows],
        }

    def _query_dimension(self, conn: Any, expression: str, where: str, params: list[Any], limit: int) -> list[Any]:
        return conn.execute(
            f"""
            SELECT
                {expression} AS key,
                {self.SUMMARY_COLUMNS}
            FROM platform_usage_records
            {where}
            GROUP BY key
            ORDER BY total_tokens DESC, request_count DESC, key ASC
            LIMIT %s
            """,
            tuple([*params, limit]),
        ).fetchall()

    @staticmethod
    def _query_metadata_counts(
        conn: Any,
        metadata_key: str,
        where: str,
        params: list[Any],
        limit: int,
        prefix: str = "",
    ) -> list[Any]:
        entry_conditions: list[str] = []
        entry_params: list[Any] = []
        if prefix:
            entry_conditions.append("LEFT(entry.key, %s) = %s")
            entry_params.extend([len(prefix), prefix])
        if entry_conditions:
            entry_clause = " AND ".join(entry_conditions)
            combined_where = f"{where} AND {entry_clause}" if where else f"WHERE {entry_clause}"
        else:
            combined_where = where
        return conn.execute(
            f"""
            SELECT
                entry.key AS key,
                COALESCE(SUM(
                    CASE WHEN entry.value ~ '^[0-9]+$' THEN entry.value::integer ELSE 0 END
                ), 0) AS count
            FROM platform_usage_records
            CROSS JOIN LATERAL jsonb_each_text(COALESCE(metadata -> %s, '{{}}'::jsonb)) AS entry(key, value)
            {combined_where}
            GROUP BY entry.key
            ORDER BY count DESC, entry.key ASC
            LIMIT %s
            """,
            tuple([metadata_key, *params, *entry_params, limit]),
        ).fetchall()

    @staticmethod
    def _build_conditions(
        *,
        tenant_id: str = "",
        agent_id: str = "",
        day: str = "",
        start: str = "",
        end: str = "",
        model: str = "",
    ) -> tuple[list[str], list[Any]]:
        conditions: list[str] = []
        params: list[Any] = []
        if tenant_id:
            conditions.append("tenant_id = %s")
            params.append(tenant_id)
        if agent_id:
            conditions.append("agent_id = %s")
            params.append(agent_id)
        if model:
            conditions.append("model = %s")
            params.append(model)
        if start:
            conditions.append("created_at >= %s")
            params.append(start)
        if end:
            conditions.append("created_at < %s")
            params.append(end)
        if day:
            conditions.append("created_at LIKE %s")
            params.append(f"{day}%")
        return conditions, params

    @staticmethod
    def _summary_from_row(row: Any) -> dict[str, Any]:
        if not row:
            return {
                "request_count": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "provider_request_count": 0,
                "estimated_request_count": 0,
                "tool_call_count": 0,
                "mcp_call_count": 0,
                "tool_error_count": 0,
                "tool_execution_time_ms": 0,
                "estimated_cost": 0.0,
            }
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

    @classmethod
    def _dimension_from_row(cls, row: Any) -> dict[str, Any]:
        item = cls._summary_from_row(row)
        item["key"] = row["key"] or "unknown"
        return item

    @staticmethod
    def _count_from_row(row: Any) -> dict[str, Any]:
        return {"key": row["key"] or "unknown", "count": int(row["count"] or 0)}

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
