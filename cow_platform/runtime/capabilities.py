from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from bridge.context import Context
from common.log import logger
from cow_platform.runtime.scope import activate_config_overrides, get_current_config_overrides
from cow_platform.services.agent_service import DEFAULT_TENANT_ID
from cow_platform.services.capability_config_service import CapabilityConfigService


def _context_tenant_id(context: Context | None) -> str:
    if context is None:
        return DEFAULT_TENANT_ID
    return (
        str(context.get("tenant_id", "") or "").strip()
        or str(context.get("source_tenant_id", "") or "").strip()
        or DEFAULT_TENANT_ID
    )


def resolve_context_capability_config(context: Context | None, capability: str):
    tenant_id = _context_tenant_id(context)
    try:
        return CapabilityConfigService().resolve_for_runtime(tenant_id, capability)
    except Exception as exc:
        logger.debug(f"[capability_runtime] no DB capability override for {capability}: {exc}")
        return None


def build_context_capability_overrides(context: Context | None, capability: str) -> dict[str, object]:
    definition = resolve_context_capability_config(context, capability)
    if definition is None:
        return {}
    overrides = CapabilityConfigService().build_runtime_overrides(definition)
    overrides["_capability_config_id"] = definition.capability_config_id
    overrides["_capability"] = definition.capability
    return overrides


@contextmanager
def activate_context_capability(context: Context | None, capability: str) -> Iterator[object | None]:
    definition = resolve_context_capability_config(context, capability)
    if definition is None:
        yield None
        return
    overrides = CapabilityConfigService().build_runtime_overrides(definition)
    current_overrides = get_current_config_overrides()
    merged = {**current_overrides, **overrides}
    merged["_capability_config_id"] = definition.capability_config_id
    merged["_capability"] = definition.capability
    with activate_config_overrides(merged):
        yield definition
