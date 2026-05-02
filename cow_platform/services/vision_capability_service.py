from __future__ import annotations

from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from typing import Iterator

from common.log import logger
from cow_platform.runtime.scope import (
    activate_config_overrides,
    get_current_config_overrides,
    get_current_runtime_context,
)
from cow_platform.services.capability_config_service import (
    CapabilityConfigService,
    provider_bot_type,
)


@dataclass(frozen=True, slots=True)
class VisionCapabilityProviderConfig:
    name: str
    provider: str
    model_name: str
    api_key: str = ""
    api_base: str = ""
    bot_type: str = ""
    use_bot: bool = False
    config_overrides: dict | None = None


class VisionCapabilityService:
    """Resolve platform multimodal capability config for the legacy vision tool."""

    def __init__(self, capability_service: CapabilityConfigService | None = None):
        self.capability_service = capability_service or CapabilityConfigService()

    def resolve_provider(self) -> VisionCapabilityProviderConfig | None:
        runtime_context = get_current_runtime_context()
        if runtime_context is None:
            return None

        definition = self.capability_service.resolve_for_runtime(
            runtime_context.tenant_id,
            "multimodal",
        )
        if definition is None:
            return None

        capability_overrides = self.capability_service.build_runtime_overrides(definition)
        overrides = {**get_current_config_overrides(), **capability_overrides}
        provider = str(definition.provider or "").strip()
        display_name = definition.display_name or provider
        model_name = definition.model_name

        if provider in {"openai", "custom", "linkai"}:
            api_base = definition.api_base or (
                "https://api.link-ai.tech" if provider == "linkai" else "https://api.openai.com/v1"
            )
            if not definition.api_key:
                return None
            return VisionCapabilityProviderConfig(
                name=display_name,
                provider=provider,
                api_key=definition.api_key,
                api_base=api_base,
                model_name=model_name,
                config_overrides=overrides,
            )

        bot_type = provider_bot_type(provider)
        if not bot_type:
            return None
        return VisionCapabilityProviderConfig(
            name=display_name,
            provider=provider,
            model_name=model_name,
            bot_type=bot_type,
            use_bot=True,
            config_overrides=overrides,
        )

    def create_bot(self, provider: VisionCapabilityProviderConfig):
        if not provider.use_bot or not provider.bot_type:
            return None
        from models.bot_factory import create_bot

        with activate_vision_provider_overrides(provider.config_overrides or {}):
            bot = create_bot(provider.bot_type)
        if not hasattr(bot, "call_vision"):
            logger.debug(
                f"[VisionCapabilityService] provider {provider.provider} bot "
                f"{provider.bot_type} does not support call_vision"
            )
            return None
        return bot


@contextmanager
def activate_vision_provider_overrides(config_overrides: dict | None) -> Iterator[None]:
    if not config_overrides:
        with nullcontext():
            yield
        return
    with activate_config_overrides({**get_current_config_overrides(), **dict(config_overrides)}):
        yield
