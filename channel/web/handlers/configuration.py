from __future__ import annotations

import json
import os
from collections import OrderedDict

import web

from common import const
from common.log import logger
from config import conf
from channel.web.handlers.dependencies import (
    _is_platform_admin_session,
    _is_tenant_auth_enabled,
    _register_platform_admin,
    _require_auth,
    _require_platform_admin,
)

class AuthPlatformRegisterHandler:
    def POST(self):
        web.header("Content-Type", "application/json; charset=utf-8")
        try:
            data = json.loads(web.data())
        except Exception:
            return json.dumps({"status": "error", "message": "Invalid request"})
        return json.dumps(_register_platform_admin(data), ensure_ascii=False)

class ConfigHandler:

    _RECOMMENDED_MODELS = [
        const.MINIMAX_M2_7, const.MINIMAX_M2_5, const.MINIMAX_M2_1, const.MINIMAX_M2_1_LIGHTNING,
        const.GLM_5_TURBO, const.GLM_5, const.GLM_4_7,
        const.QWEN36_PLUS, const.QWEN35_PLUS, const.QWEN3_MAX,
        const.KIMI_K2_5, const.KIMI_K2,
        const.DOUBAO_SEED_2_PRO, const.DOUBAO_SEED_2_CODE,
        const.CLAUDE_4_6_SONNET, const.CLAUDE_4_6_OPUS, const.CLAUDE_4_5_SONNET,
        const.GEMINI_31_FLASH_LITE_PRE, const.GEMINI_31_PRO_PRE, const.GEMINI_3_FLASH_PRE,
        const.GPT_54, const.GPT_54_MINI, const.GPT_54_NANO, const.GPT_5, const.GPT_41, const.GPT_4o,
        const.DEEPSEEK_CHAT, const.DEEPSEEK_REASONER,
    ]

    PROVIDER_MODELS = OrderedDict([
        ("minimax", {
            "label": "MiniMax",
            "api_key_field": "minimax_api_key",
            "api_base_key": None,
            "api_base_default": None,
            "models": [const.MINIMAX_M2_7, const.MINIMAX_M2_7_HIGHSPEED, const.MINIMAX_M2_5, const.MINIMAX_M2_1, const.MINIMAX_M2_1_LIGHTNING],
        }),
        ("zhipu", {
            "label": "智谱AI",
            "api_key_field": "zhipu_ai_api_key",
            "api_base_key": "zhipu_ai_api_base",
            "api_base_default": "https://open.bigmodel.cn/api/paas/v4",
            "models": [const.GLM_5_TURBO, const.GLM_5, const.GLM_4_7],
        }),
        ("dashscope", {
            "label": "通义千问",
            "api_key_field": "dashscope_api_key",
            "api_base_key": None,
            "api_base_default": None,
            "models": [const.QWEN36_PLUS, const.QWEN35_PLUS, const.QWEN3_MAX],
        }),
        ("moonshot", {
            "label": "Kimi",
            "api_key_field": "moonshot_api_key",
            "api_base_key": "moonshot_base_url",
            "api_base_default": "https://api.moonshot.cn/v1",
            "models": [const.KIMI_K2_5, const.KIMI_K2],
        }),
        ("doubao", {
            "label": "豆包",
            "api_key_field": "ark_api_key",
            "api_base_key": "ark_base_url",
            "api_base_default": "https://ark.cn-beijing.volces.com/api/v3",
            "models": [const.DOUBAO_SEED_2_PRO, const.DOUBAO_SEED_2_CODE],
        }),
        ("claudeAPI", {
            "label": "Claude",
            "api_key_field": "claude_api_key",
            "api_base_key": "claude_api_base",
            "api_base_default": "https://api.anthropic.com/v1",
            "models": [const.CLAUDE_4_6_SONNET, const.CLAUDE_4_6_OPUS, const.CLAUDE_4_5_SONNET],
        }),
        ("gemini", {
            "label": "Gemini",
            "api_key_field": "gemini_api_key",
            "api_base_key": "gemini_api_base",
            "api_base_default": "https://generativelanguage.googleapis.com",
            "models": [const.GEMINI_31_FLASH_LITE_PRE, const.GEMINI_31_PRO_PRE, const.GEMINI_3_FLASH_PRE],
        }),
        ("openai", {
            "label": "OpenAI",
            "api_key_field": "open_ai_api_key",
            "api_base_key": "open_ai_api_base",
            "api_base_default": "https://api.openai.com/v1",
            "models": [const.GPT_54, const.GPT_54_MINI, const.GPT_54_NANO, const.GPT_5, const.GPT_41, const.GPT_4o],
        }),
        ("deepseek", {
            "label": "DeepSeek",
            "api_key_field": "deepseek_api_key",
            "api_base_key": "deepseek_api_base",
            "api_base_default": "https://api.deepseek.com/v1",
            "models": [const.DEEPSEEK_CHAT, const.DEEPSEEK_REASONER],
        }),
        ("modelscope", {
            "label": "ModelScope",
            "api_key_field": "modelscope_api_key",
            "api_base_key": None,
            "api_base_default": None,
            "models": [const.QWEN3_5_27B, const.QWEN3_235B_A22B_INSTRUCT_2507],
        }),
        ("linkai", {
            "label": "LinkAI",
            "api_key_field": "linkai_api_key",
            "api_base_key": None,
            "api_base_default": None,
            "models": _RECOMMENDED_MODELS,
        }),
    ])

    EDITABLE_KEYS = {
        "model", "bot_type", "use_linkai",
        "open_ai_api_base", "deepseek_api_base", "claude_api_base", "gemini_api_base",
        "zhipu_ai_api_base", "moonshot_base_url", "ark_base_url",
        "open_ai_api_key", "deepseek_api_key", "claude_api_key", "gemini_api_key",
        "zhipu_ai_api_key", "dashscope_api_key", "moonshot_api_key",
        "ark_api_key", "minimax_api_key", "linkai_api_key", "modelscope_api_key",
        "agent_max_context_tokens", "agent_max_context_turns", "agent_max_steps",
        "enable_thinking", "web_password",
    }

    @staticmethod
    def _mask_key(value: str) -> str:
        """Mask the middle part of an API key for display."""
        if not value or len(value) <= 8:
            return value
        return value[:4] + "*" * (len(value) - 8) + value[-4:]

    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            local_config = conf()
            use_agent = local_config.get("agent", False)
            title = "CowAgent" if use_agent else "AI Assistant"
            if _is_tenant_auth_enabled() and not _is_platform_admin_session():
                return json.dumps({
                    "status": "success",
                    "use_agent": use_agent,
                    "title": title,
                    "channel_type": local_config.get("channel_type", ""),
                    "agent_max_context_tokens": local_config.get("agent_max_context_tokens", 50000),
                    "agent_max_context_turns": local_config.get("agent_max_context_turns", 20),
                    "agent_max_steps": local_config.get("agent_max_steps", 20),
                    "enable_thinking": bool(local_config.get("enable_thinking", True)),
                }, ensure_ascii=False)

            api_bases = {}
            api_keys_masked = {}
            for pid, pinfo in self.PROVIDER_MODELS.items():
                base_key = pinfo.get("api_base_key")
                if base_key:
                    api_bases[base_key] = local_config.get(base_key, pinfo["api_base_default"])
                key_field = pinfo.get("api_key_field")
                if key_field and key_field not in api_keys_masked:
                    raw = local_config.get(key_field, "")
                    api_keys_masked[key_field] = self._mask_key(raw) if raw else ""

            providers = {}
            for pid, p in self.PROVIDER_MODELS.items():
                providers[pid] = {
                    "label": p["label"],
                    "models": p["models"],
                    "api_base_key": p["api_base_key"],
                    "api_base_default": p["api_base_default"],
                    "api_key_field": p.get("api_key_field"),
                }

            raw_pwd = local_config.get("web_password", "")
            masked_pwd = ("*" * len(raw_pwd)) if raw_pwd else ""

            return json.dumps({
                "status": "success",
                "use_agent": use_agent,
                "title": title,
                "model": local_config.get("model", ""),
                "bot_type": "openai" if local_config.get("bot_type") == "chatGPT" else local_config.get("bot_type", ""),
                "use_linkai": bool(local_config.get("use_linkai", False)),
                "channel_type": local_config.get("channel_type", ""),
                "agent_max_context_tokens": local_config.get("agent_max_context_tokens", 50000),
                "agent_max_context_turns": local_config.get("agent_max_context_turns", 20),
                "agent_max_steps": local_config.get("agent_max_steps", 20),
                "enable_thinking": bool(local_config.get("enable_thinking", True)),
                "api_bases": api_bases,
                "api_keys": api_keys_masked,
                "providers": providers,
                "web_password_masked": masked_pwd,
            }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        if _is_tenant_auth_enabled():
            _require_platform_admin()
        else:
            _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            data = json.loads(web.data())
            updates = data.get("updates", {})
            if not updates:
                return json.dumps({"status": "error", "message": "no updates provided"})

            local_config = conf()
            applied = {}
            for key, value in updates.items():
                if key not in self.EDITABLE_KEYS:
                    continue
                if key in ("agent_max_context_tokens", "agent_max_context_turns", "agent_max_steps"):
                    value = int(value)
                if key in ("use_linkai", "enable_thinking"):
                    value = bool(value)
                local_config[key] = value
                applied[key] = value

            if not applied:
                return json.dumps({"status": "error", "message": "no valid keys to update"})

            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))), "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    file_cfg = json.load(f)
            else:
                file_cfg = {}
            file_cfg.update(applied)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(file_cfg, f, indent=4, ensure_ascii=False)

            logger.info(f"[WebChannel] Config updated: {list(applied.keys())}")
            return json.dumps({"status": "success", "applied": applied}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return json.dumps({"status": "error", "message": str(e)})


__all__ = ["AuthPlatformRegisterHandler", "ConfigHandler"]
