from common import const
from common.model_routing import resolve_bot_type_from_model


def test_shared_model_routing_covers_vendor_prefixes():
    assert resolve_bot_type_from_model("qwen3.6-plus") == const.QWEN_DASHSCOPE
    assert resolve_bot_type_from_model("claude-sonnet-4-6") == const.CLAUDEAPI
    assert resolve_bot_type_from_model("MiniMax-M2.7") == const.MiniMax
    assert resolve_bot_type_from_model("deepseek-reasoner") == const.DEEPSEEK
