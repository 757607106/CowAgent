from collections import OrderedDict
import hashlib

from models.bot_factory import create_bot
from bridge.context import Context
from bridge.reply import Reply
from common import const
from common.log import logger
from common.model_routing import normalize_model_name, resolve_bot_type_from_model
from common.singleton import singleton
from config import conf
from translate.factory import create_translator
from voice.factory import create_voice


_BOT_CACHE_LIMIT = 64
_SECRET_KEY_MARKERS = ("key", "secret", "token", "password", "cookie")


@singleton
class Bridge(object):
    def __init__(self):
        self.btype = {
            "chat": const.OPENAI,
            "voice_to_text": conf().get("voice_to_text", "openai"),
            "text_to_voice": conf().get("text_to_voice", "google"),
            "translate": conf().get("translate", "baidu"),
        }
        # 这边取配置的模型
        bot_type = conf().get("bot_type")
        if bot_type:
            self.btype["chat"] = bot_type
        else:
            raw_model_type = conf().get("model") or const.GPT_41_MINI
            model_type = normalize_model_name(raw_model_type)
            if raw_model_type != model_type:
                logger.warning(
                    f"[Bridge] model_type is not a string: {raw_model_type} "
                    f"(type: {type(raw_model_type).__name__}), converting to string"
                )
            if conf().get("use_azure_chatgpt", False):
                self.btype["chat"] = const.CHATGPTONAZURE
            else:
                self.btype["chat"] = resolve_bot_type_from_model(model_type, default=const.OPENAI)

            if conf().get("use_linkai") and conf().get("linkai_api_key"):
                self.btype["chat"] = const.LINKAI
                if not conf().get("voice_to_text") or conf().get("voice_to_text") in ["openai"]:
                    self.btype["voice_to_text"] = const.LINKAI
                if not conf().get("text_to_voice") or conf().get("text_to_voice") in ["openai", const.TTS_1, const.TTS_1_HD]:
                    self.btype["text_to_voice"] = const.LINKAI

        self.bots = OrderedDict()
        self.chat_bots = {}
        self._agent_bridge = None

    def _runtime_bot_type(self, typename):
        if typename == "voice_to_text":
            return conf().get("voice_to_text", self.btype[typename])
        if typename == "text_to_voice":
            return conf().get("text_to_voice", self.btype[typename])
        if typename == "translate":
            return conf().get("translate", self.btype[typename])
        if typename == "chat":
            return conf().get("bot_type") or self.btype[typename]
        return self.btype[typename]

    def _freeze_runtime_value(self, key, value):
        if isinstance(value, dict):
            return tuple(sorted((k, self._freeze_runtime_value(k, v)) for k, v in value.items()))
        if isinstance(value, (list, tuple, set)):
            return tuple(self._freeze_runtime_value(key, item) for item in value)
        if isinstance(value, str) and any(marker in key.lower() for marker in _SECRET_KEY_MARKERS):
            return ("sha256", hashlib.sha256(value.encode("utf-8")).hexdigest())
        return value

    def _runtime_bot_cache_key(self, typename):
        try:
            from cow_platform.runtime.scope import get_current_config_overrides

            overrides = tuple(
                sorted(
                    (key, self._freeze_runtime_value(key, value))
                    for key, value in get_current_config_overrides().items()
                )
            )
        except Exception:
            overrides = ()
        return (typename, self._runtime_bot_type(typename), overrides)

    # 模型对应的接口
    def get_bot(self, typename):
        cache_key = self._runtime_bot_cache_key(typename)
        bot_type = self._runtime_bot_type(typename)
        if cache_key in self.bots:
            self.bots.move_to_end(cache_key)
            return self.bots[cache_key]
        if self.bots.get(cache_key) is None:
            logger.info("create bot {} for {}".format(bot_type, typename))
            if typename == "text_to_voice":
                self.bots[cache_key] = create_voice(bot_type)
            elif typename == "voice_to_text":
                self.bots[cache_key] = create_voice(bot_type)
            elif typename == "chat":
                self.bots[cache_key] = create_bot(bot_type)
            elif typename == "translate":
                self.bots[cache_key] = create_translator(bot_type)
            while len(self.bots) > _BOT_CACHE_LIMIT:
                removed_key, _ = self.bots.popitem(last=False)
                logger.info("[Bridge] evicted runtime bot cache: {}".format(removed_key[:2]))
        return self.bots[cache_key]

    def get_bot_type(self, typename):
        return self._runtime_bot_type(typename)

    def fetch_reply_content(self, query, context: Context) -> Reply:
        return self.get_bot("chat").reply(query, context)

    def fetch_voice_to_text(self, voiceFile) -> Reply:
        return self.get_bot("voice_to_text").voiceToText(voiceFile)

    def fetch_text_to_voice(self, text) -> Reply:
        return self.get_bot("text_to_voice").textToVoice(text)

    def fetch_translate(self, text, from_lang="", to_lang="en") -> Reply:
        return self.get_bot("translate").translate(text, from_lang, to_lang)

    def find_chat_bot(self, bot_type: str):
        if self.chat_bots.get(bot_type) is None:
            self.chat_bots[bot_type] = create_bot(bot_type)
        return self.chat_bots.get(bot_type)

    def reset_bot(self):
        """
        重置bot路由
        """
        self.__init__()

    def get_agent_bridge(self):
        """
        Get agent bridge for agent-based conversations
        """
        if self._agent_bridge is None:
            from bridge.agent_bridge import AgentBridge
            self._agent_bridge = AgentBridge(self)
        return self._agent_bridge

    def cancel_running_agent(self, session_id: str, *, cache_key: str = "", context: Context = None):
        """Cancel the currently running agent task for the given session.

        This is the entry-point that ChatChannel.produce() calls when a new
        message arrives for a session that already has an in-flight request.
        If agent mode is not active or no task is running, this is a no-op.

        Args:
            session_id: The session whose running task should be cancelled.
        """
        if self._agent_bridge is not None:
            if cache_key or context is not None:
                self._agent_bridge.cancel_running_session(session_id, cache_key=cache_key, context=context)
            else:
                self._agent_bridge.cancel_running_session(session_id)

    def fetch_agent_reply(self, query: str, context: Context = None,
                          on_event=None, clear_history: bool = False) -> Reply:
        """
        Use super agent to handle the query

        Args:
            query: User query
            context: Context object
            on_event: Event callback for streaming
            clear_history: Whether to clear conversation history

        Returns:
            Reply object
        """
        agent_bridge = self.get_agent_bridge()
        return agent_bridge.agent_reply(query, context, on_event, clear_history)
