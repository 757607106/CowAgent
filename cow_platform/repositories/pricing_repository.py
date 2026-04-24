from __future__ import annotations

from dataclasses import asdict
from typing import Any

from cow_platform.db import connect, jsonb
from cow_platform.domain.models import PricingDefinition


class PostgresPricingRepository:
    """PostgreSQL-backed pricing catalog."""

    def list_pricing(self) -> list[PricingDefinition]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT model, input_price_per_million, output_price_per_million,
                       currency, metadata
                FROM platform_pricing
                ORDER BY model
                """
            ).fetchall()
        return [self._to_definition(row) for row in rows]

    def get_pricing(self, model: str) -> PricingDefinition | None:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT model, input_price_per_million, output_price_per_million,
                       currency, metadata
                FROM platform_pricing
                WHERE model = %s
                """,
                (model,),
            ).fetchone()
        return self._to_definition(row) if row else None

    def upsert_pricing(
        self,
        *,
        model: str,
        input_price_per_million: float,
        output_price_per_million: float,
        currency: str = "CNY",
        metadata: dict[str, Any] | None = None,
    ) -> PricingDefinition:
        with connect() as conn:
            row = conn.execute(
                """
                INSERT INTO platform_pricing
                    (model, input_price_per_million, output_price_per_million, currency, metadata)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (model)
                DO UPDATE SET
                    input_price_per_million = EXCLUDED.input_price_per_million,
                    output_price_per_million = EXCLUDED.output_price_per_million,
                    currency = EXCLUDED.currency,
                    metadata = EXCLUDED.metadata
                RETURNING model, input_price_per_million, output_price_per_million,
                          currency, metadata
                """,
                (
                    model,
                    float(input_price_per_million),
                    float(output_price_per_million),
                    currency,
                    jsonb(metadata or {}),
                ),
            ).fetchone()
            conn.commit()
        return self._to_definition(row)

    def export_record(self, definition: PricingDefinition) -> dict[str, Any]:
        return asdict(definition)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> PricingDefinition:
        return PricingDefinition(
            model=record["model"],
            input_price_per_million=float(record.get("input_price_per_million", 0.0)),
            output_price_per_million=float(record.get("output_price_per_million", 0.0)),
            currency=record.get("currency", "CNY"),
            metadata=record.get("metadata", {}) or {},
        )


PricingRepository = PostgresPricingRepository
