from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from config import build_config_environment
from cow_platform.runtime.scope import get_current_config_overrides


def build_runtime_environment(
    overrides: Mapping[str, Any] | None = None,
    *,
    base_env: Mapping[str, str] | None = None,
    extra_env: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Build a subprocess environment from the current platform runtime scope.

    The order is stable and deliberate:
    host env / caller env < current runtime overrides < explicit overrides < extra env.
    """
    env = dict(os.environ if base_env is None else base_env)
    effective_overrides = get_current_config_overrides()
    if overrides:
        effective_overrides.update(dict(overrides))
    env.update(build_config_environment(effective_overrides))
    if extra_env:
        env.update({key: str(value) for key, value in extra_env.items() if value is not None})
    return env
