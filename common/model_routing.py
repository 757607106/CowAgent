from __future__ import annotations

from common import const


MODEL_BOT_TYPE_MAP = {
    "text-davinci-003": const.OPEN_AI,
    "wenxin": const.BAIDU,
    "wenxin-4": const.BAIDU,
    "xunfei": const.XUNFEI,
    const.QWEN: const.QWEN_DASHSCOPE,
    const.QWEN_TURBO: const.QWEN_DASHSCOPE,
    const.QWEN_PLUS: const.QWEN_DASHSCOPE,
    const.QWEN_MAX: const.QWEN_DASHSCOPE,
    const.MODELSCOPE: const.MODELSCOPE,
    const.MOONSHOT: const.MOONSHOT,
    "moonshot-v1-8k": const.MOONSHOT,
    "moonshot-v1-32k": const.MOONSHOT,
    "moonshot-v1-128k": const.MOONSHOT,
    "abab6.5-chat": const.MiniMax,
    "abab6.5": const.MiniMax,
}


MODEL_PREFIX_BOT_TYPE_MAP = (
    ("qwen", const.QWEN_DASHSCOPE),
    ("qwq", const.QWEN_DASHSCOPE),
    ("qvq", const.QWEN_DASHSCOPE),
    ("gemini", const.GEMINI),
    ("glm", const.ZHIPU_AI),
    ("claude", const.CLAUDEAPI),
    ("moonshot", const.MOONSHOT),
    ("kimi", const.MOONSHOT),
    ("doubao", const.DOUBAO),
    ("deepseek", const.DEEPSEEK),
    ("minimax", const.MiniMax),
)


def normalize_model_name(model_name) -> str:
    if isinstance(model_name, str):
        return model_name
    return "" if model_name is None else str(model_name)


def resolve_bot_type_from_model(model_name, *, default: str = const.OPENAI) -> str:
    resolved = normalize_model_name(model_name)
    if not resolved:
        return default
    if resolved in MODEL_BOT_TYPE_MAP:
        return MODEL_BOT_TYPE_MAP[resolved]
    lowered = resolved.lower()
    for prefix, bot_type in MODEL_PREFIX_BOT_TYPE_MAP:
        if lowered.startswith(prefix):
            return bot_type
    return default
