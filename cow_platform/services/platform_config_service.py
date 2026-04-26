from __future__ import annotations

import json
import time
from typing import Any, Iterable

from cow_platform.db import connect


PLATFORM_CONFIG_KEYS = {
    "model",
    "bot_type",
    "use_linkai",
    "open_ai_api_base",
    "deepseek_api_base",
    "claude_api_base",
    "gemini_api_base",
    "zhipu_ai_api_base",
    "moonshot_base_url",
    "ark_base_url",
    "open_ai_api_key",
    "deepseek_api_key",
    "claude_api_key",
    "gemini_api_key",
    "zhipu_ai_api_key",
    "dashscope_api_key",
    "moonshot_api_key",
    "ark_api_key",
    "minimax_api_key",
    "linkai_api_key",
    "modelscope_api_key",
    "agent",
    "agent_workspace",
    "agent_max_context_tokens",
    "agent_max_context_turns",
    "agent_max_steps",
    "conversation_persistence",
    "enable_thinking",
    "knowledge",
    "web_console",
    "web_password",
    "web_port",
    "web_tenant_auth",
}

_BOOL_KEYS = {
    "agent",
    "conversation_persistence",
    "enable_thinking",
    "knowledge",
    "use_linkai",
    "web_console",
    "web_tenant_auth",
}
_INT_KEYS = {
    "agent_max_context_tokens",
    "agent_max_context_turns",
    "agent_max_steps",
    "web_port",
}


class PlatformConfigService:
    """Platform-wide runtime settings backed by ``platform_settings``.

    Tenant-owned resources such as channel configs, model configs, agents, MCP,
    skills and bindings have their own tenant-scoped tables. This service is
    only for platform-level runtime settings that used to live in ``config.json``.
    """

    def list_settings(self, keys: Iterable[str] | None = None) -> dict[str, Any]:
        selected = [key for key in (keys or PLATFORM_CONFIG_KEYS) if key in PLATFORM_CONFIG_KEYS]
        if not selected:
            return {}
        placeholders = ", ".join(["%s"] * len(selected))
        with connect() as conn:
            rows = conn.execute(
                f"SELECT key, value FROM platform_settings WHERE key IN ({placeholders})",
                tuple(selected),
            ).fetchall()
        return {row["key"]: self._decode_value(row["key"], row["value"]) for row in rows}

    def update_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        normalized = {
            key: self._normalize_value(key, value)
            for key, value in (updates or {}).items()
            if key in PLATFORM_CONFIG_KEYS
        }
        if not normalized:
            return {}
        now = int(time.time())
        with connect() as conn:
            for key, value in normalized.items():
                conn.execute(
                    """
                    INSERT INTO platform_settings (key, value, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (key)
                    DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
                    """,
                    (key, self._encode_value(value), now),
                )
            conn.commit()
        return normalized

    @staticmethod
    def _encode_value(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    @classmethod
    def _decode_value(cls, key: str, raw: str) -> Any:
        try:
            value = json.loads(raw)
        except Exception:
            value = raw
        return cls._normalize_value(key, value)

    @staticmethod
    def _normalize_value(key: str, value: Any) -> Any:
        if key in _BOOL_KEYS:
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "on"}
            return bool(value)
        if key in _INT_KEYS:
            return int(value)
        if value is None:
            return ""
        return value
