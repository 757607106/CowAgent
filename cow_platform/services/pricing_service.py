from __future__ import annotations

from cow_platform.domain.models import PricingDefinition
from cow_platform.repositories.pricing_repository import FilePricingRepository


class PricingService:
    """当前阶段使用的定价服务。"""

    def __init__(self, repository: FilePricingRepository | None = None):
        self.repository = repository or FilePricingRepository()

    def list_pricing(self) -> list[PricingDefinition]:
        return self.repository.list_pricing()

    def resolve_pricing(self, model: str) -> PricingDefinition:
        resolved_model = model or "unknown"
        definition = self.repository.get_pricing(resolved_model)
        if definition is not None:
            return definition
        return PricingDefinition(model=resolved_model, input_price_per_million=0.0, output_price_per_million=0.0)

    def upsert_pricing(
        self,
        *,
        model: str,
        input_price_per_million: float,
        output_price_per_million: float,
        currency: str = "CNY",
    ) -> dict:
        definition = self.repository.upsert_pricing(
            model=model,
            input_price_per_million=input_price_per_million,
            output_price_per_million=output_price_per_million,
            currency=currency,
        )
        return self.serialize_pricing(definition)

    def serialize_pricing(self, definition: PricingDefinition) -> dict:
        return self.repository.export_record(definition)

    def list_pricing_records(self) -> list[dict]:
        return [self.serialize_pricing(item) for item in self.list_pricing()]
