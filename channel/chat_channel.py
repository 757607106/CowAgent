import os
import re
import threading
import time
from asyncio import CancelledError
from concurrent.futures import Future, ThreadPoolExecutor

from bridge.bridge import Bridge
from bridge.context import *
from bridge.reply import *
from channel.channel import Channel
from common.dequeue import Dequeue
from common import memory
from plugins import *

try:
    from voice.audio_convert import any_to_wav
except Exception as e:
    pass

handler_pool = ThreadPoolExecutor(max_workers=8)  # 处理消息的线程池


# 抽象类, 它包含了与消息通道无关的通用处理逻辑
class ChatChannel(Channel):
    name = None  # 登录的用户名
    user_id = None  # 登录的用户id

    def __init__(self):
        super().__init__()
        # Instance-level attributes so each channel subclass has its own
        # independent session queue and lock. Previously these were class-level,
        # which caused contexts from one channel (e.g. Feishu) to be consumed
        # by another channel's consume() thread (e.g. Web), leading to errors
        # like "No request_id found in context".
        self.futures = {}
        self.sessions = {}
        self.lock = threading.Lock()
        _thread = threading.Thread(target=self.consume)
        _thread.daemon = True
        _thread.start()

    def _apply_platform_runtime_target(self, context: Context):
        """Best-effort binding resolution for non-web channels using channel metadata."""
        if context is None or not conf().get("agent", False):
            return context

        channel_config_id = str(context.get("channel_config_id", "") or "").strip()
        source_tenant_id = str(context.get("source_tenant_id", "") or "").strip()
        tenant_managed = bool(channel_config_id or source_tenant_id)
        if (
            not tenant_managed
            and (context.get("binding_id") or (context.get("tenant_id") and context.get("agent_id")))
        ):
            return context

        cmsg = context.get("msg")
        if cmsg is None:
            if tenant_managed:
                logger.warning(
                    "[chat_channel] managed channel context missing message metadata: "
                    f"tenant={source_tenant_id}, channel_config_id={channel_config_id}"
                )
                return None
            return context

        external_app_id = str(getattr(cmsg, "to_user_id", "") or "").strip()
        external_chat_id = str(getattr(cmsg, "other_user_id", "") or "").strip()
        external_user_id = str(
            getattr(cmsg, "actual_user_id", "") or getattr(cmsg, "from_user_id", "") or ""
        ).strip()

        if not any((external_app_id, external_chat_id, external_user_id)):
            if tenant_managed:
                logger.warning(
                    "[chat_channel] managed channel context missing external identity: "
                    f"tenant={source_tenant_id}, channel_config_id={channel_config_id}"
                )
                return None
            return context

        try:
            from cow_platform.services.binding_service import ChannelBindingService

            binding = ChannelBindingService().resolve_binding_for_channel(
                channel_type=context.get("channel_type", "") or self.channel_type,
                channel_config_id=channel_config_id,
                external_app_id=external_app_id,
                external_chat_id=external_chat_id,
                external_user_id=external_user_id,
            )
        except Exception as e:
            logger.warning(f"[chat_channel] binding resolution failed: {e}")
            if tenant_managed:
                return None
            return context

        if binding is None:
            if tenant_managed:
                logger.warning(
                    "[chat_channel] no tenant binding matched for managed channel: "
                    f"tenant={source_tenant_id}, channel_config_id={channel_config_id}, "
                    f"channel_type={context.get('channel_type', '') or self.channel_type}, "
                    f"app={external_app_id}, chat={external_chat_id}, user={external_user_id}"
                )
                return None
            return context

        if source_tenant_id and binding.tenant_id != source_tenant_id:
            logger.error(
                "[chat_channel] tenant binding mismatch for managed channel: "
                f"source_tenant={source_tenant_id}, binding_tenant={binding.tenant_id}, "
                f"binding_id={binding.binding_id}, channel_config_id={channel_config_id}"
            )
            return None

        context["binding_id"] = binding.binding_id
        context["tenant_id"] = binding.tenant_id
        context["agent_id"] = binding.agent_id
        context["binding_metadata"] = {
            "channel_config_id": context.get("channel_config_id", ""),
            "external_app_id": external_app_id,
            "external_chat_id": external_chat_id,
            "external_user_id": external_user_id,
        }

        # Best-effort tenant user resolution for governance/authorization context.
        if external_user_id:
            try:
                from cow_platform.services.tenant_user_service import TenantUserService

                tenant_user = TenantUserService().resolve_user_by_identity(
                    tenant_id=binding.tenant_id,
                    channel_type=context.get("channel_type", "") or self.channel_type,
                    external_user_id=external_user_id,
                )
                if tenant_user is not None:
                    context["tenant_user_id"] = tenant_user.user_id
                    context["tenant_user_role"] = tenant_user.role
                    context["tenant_user_status"] = tenant_user.status
            except Exception as e:
                logger.warning(f"[chat_channel] tenant user resolution failed: {e}")
        return context

    # 根据消息构造context，消息内容相关的触发项写在这里
    def _compose_context(self, ctype: ContextType, content, **kwargs):
        context = Context(ctype, content)
        context.kwargs = kwargs
        if "channel_type" not in context:
            context["channel_type"] = self.channel_type
        if self.channel_config_id and "channel_config_id" not in context:
            context["channel_config_id"] = self.channel_config_id
        if self.tenant_id and "source_tenant_id" not in context:
            context["source_tenant_id"] = self.tenant_id
        if "origin_ctype" not in context:
            context["origin_ctype"] = ctype
        # context首次传入时，receiver是None，根据类型设置receiver
        first_in = "receiver" not in context
        # 群名匹配过程，设置session_id和receiver
        if first_in:  # context首次传入时，receiver是None，根据类型设置receiver
            config = conf()
            cmsg = context["msg"]
            user_data = conf().get_user_data(cmsg.from_user_id)
            context["openai_api_key"] = user_data.get("openai_api_key")
            context["gpt_model"] = user_data.get("gpt_model")
            if context.get("isgroup", False):
                group_name = cmsg.other_user_nickname
                group_id = cmsg.other_user_id

                group_name_white_list = config.get("group_name_white_list", [])
                group_name_keyword_white_list = config.get("group_name_keyword_white_list", [])
                if any(
                    [
                        group_name in group_name_white_list,
                        "ALL_GROUP" in group_name_white_list,
                        check_contain(group_name, group_name_keyword_white_list),
                    ]
                ):
                    # Check global group_shared_session config first
                    group_shared_session = conf().get("group_shared_session", True)
                    if group_shared_session:
                        # All users in the group share the same session
                        session_id = group_id
                    else:
                        # Check group-specific whitelist (legacy behavior)
                        group_chat_in_one_session = conf().get("group_chat_in_one_session", [])
                        session_id = cmsg.actual_user_id
                        if any(
                            [
                                group_name in group_chat_in_one_session,
                                "ALL_GROUP" in group_chat_in_one_session,
                            ]
                        ):
                            session_id = group_id
                else:
                    logger.debug(f"No need reply, groupName not in whitelist, group_name={group_name}")
                    return None
                context["session_id"] = session_id
                context["receiver"] = group_id
            else:
                context["session_id"] = cmsg.other_user_id
                context["receiver"] = cmsg.other_user_id
            e_context = PluginManager().emit_event(EventContext(Event.ON_RECEIVE_MESSAGE, {"channel": self, "context": context}))
            context = e_context["context"]
            if e_context.is_pass() or context is None:
                return context
            if cmsg.from_user_id == self.user_id and not config.get("trigger_by_self", True):
                logger.debug("[chat_channel]self message skipped")
                return None
            context = self._apply_platform_runtime_target(context)
            if context is None:
                return None

        # 消息内容匹配过程，并处理content
        if ctype == ContextType.TEXT:
            if first_in and "」\n- - - - - - -" in content:  # 初次匹配 过滤引用消息
                logger.debug(content)
                logger.debug("[chat_channel]reference query skipped")
                return None

            nick_name_black_list = conf().get("nick_name_black_list", [])
            if context.get("isgroup", False):  # 群聊
                # 校验关键字
                match_prefix = check_prefix(content, conf().get("group_chat_prefix"))
                match_contain = check_contain(content, conf().get("group_chat_keyword"))
                flag = False
                if context["msg"].to_user_id != context["msg"].actual_user_id:
                    if match_prefix is not None or match_contain is not None:
                        flag = True
                        if match_prefix:
                            content = content.replace(match_prefix, "", 1).strip()
                    if context["msg"].is_at:
                        nick_name = context["msg"].actual_user_nickname
                        if nick_name and nick_name in nick_name_black_list:
                            # 黑名单过滤
                            logger.warning(f"[chat_channel] Nickname {nick_name} in In BlackList, ignore")
                            return None

                        logger.info("[chat_channel]receive group at")
                        if not conf().get("group_at_off", False):
                            flag = True
                        self.name = self.name if self.name is not None else ""  # 部分渠道self.name可能没有赋值
                        pattern = f"@{re.escape(self.name)}(\u2005|\u0020)"
                        subtract_res = re.sub(pattern, r"", content)
                        if isinstance(context["msg"].at_list, list):
                            for at in context["msg"].at_list:
                                pattern = f"@{re.escape(at)}(\u2005|\u0020)"
                                subtract_res = re.sub(pattern, r"", subtract_res)
                        if subtract_res == content and context["msg"].self_display_name:
                            # 前缀移除后没有变化，使用群昵称再次移除
                            pattern = f"@{re.escape(context['msg'].self_display_name)}(\u2005|\u0020)"
                            subtract_res = re.sub(pattern, r"", content)
                        content = subtract_res
                if not flag:
                    if context["origin_ctype"] == ContextType.VOICE:
                        logger.info("[chat_channel]receive group voice, but checkprefix didn't match")
                    return None
            else:  # 单聊
                nick_name = context["msg"].from_user_nickname
                if nick_name and nick_name in nick_name_black_list:
                    # 黑名单过滤
                    logger.warning(f"[chat_channel] Nickname '{nick_name}' in In BlackList, ignore")
                    return None

                match_prefix = check_prefix(content, conf().get("single_chat_prefix", [""]))
                if match_prefix is not None:  # 判断如果匹配到自定义前缀，则返回过滤掉前缀+空格后的内容
                    content = content.replace(match_prefix, "", 1).strip()
                elif context["origin_ctype"] == ContextType.VOICE:  # 如果源消息是私聊的语音消息，允许不匹配前缀，放宽条件
                    pass
                else:
                    logger.info("[chat_channel]receive single chat msg, but checkprefix didn't match")
                    return None
            content = content.strip()
            img_match_prefix = check_prefix(content, conf().get("image_create_prefix",[""]))
            if img_match_prefix:
                content = content.replace(img_match_prefix, "", 1)
                context.type = ContextType.IMAGE_CREATE
            else:
                context.type = ContextType.TEXT
            context.content = content.strip()
            if "desire_rtype" not in context and conf().get("always_reply_voice") and ReplyType.VOICE not in self.NOT_SUPPORT_REPLYTYPE:
                context["desire_rtype"] = ReplyType.VOICE
        elif context.type == ContextType.VOICE:
            if "desire_rtype" not in context and conf().get("voice_reply_voice") and ReplyType.VOICE not in self.NOT_SUPPORT_REPLYTYPE:
                context["desire_rtype"] = ReplyType.VOICE
        return context

    def _build_capability_image_reply(self, context: Context, capability_config) -> Reply:
        if capability_config is None:
            return super().build_reply_content(context.content, context)
        try:
            image_context = Context(ContextType.IMAGE_CREATE, context.content, kwargs=dict(context.kwargs))
            return Bridge().fetch_reply_content(context.content, image_context)
        except Exception as e:
            logger.exception(f"[chat_channel] image generation capability failed: {e}")
            return Reply(ReplyType.ERROR, "图片生成失败，请稍后再试")

    def _handle(self, context: Context):
        if context is None or not context.content:
            return
        from cow_platform.runtime.scope import activate_config_overrides

        with activate_config_overrides(getattr(self, "config_overrides", {}) or {}):
            logger.debug("[chat_channel] handling context: {}".format(context))
            # reply的构建步骤
            reply = self._generate_reply(context)

            logger.debug("[chat_channel] decorating reply: {}".format(reply))

            # reply的包装步骤
            if reply and reply.content:
                reply = self._decorate_reply(context, reply)

                # reply的发送步骤
                self._send_reply(context, reply)

    def _generate_reply(self, context: Context, reply: Reply = None) -> Reply:
        reply = reply or Reply()
        e_context = PluginManager().emit_event(
            EventContext(
                Event.ON_HANDLE_CONTEXT,
                {"channel": self, "context": context, "reply": reply},
            )
        )
        reply = e_context["reply"]
        if not e_context.is_pass():
            logger.debug("[chat_channel] type={}, content={}".format(context.type, context.content))
            if context.type == ContextType.TEXT or context.type == ContextType.IMAGE_CREATE:  # 文字和图片消息
                context["channel"] = e_context["channel"]
                if context.type == ContextType.IMAGE_CREATE:
                    from cow_platform.runtime.capabilities import activate_context_capability

                    with activate_context_capability(context, "image_generation") as capability_config:
                        reply = self._build_capability_image_reply(context, capability_config)
                else:
                    reply = super().build_reply_content(context.content, context)
            elif context.type == ContextType.VOICE:  # 语音消息
                cmsg = context["msg"]
                cmsg.prepare()
                file_path = context.content
                wav_path = os.path.splitext(file_path)[0] + ".wav"
                try:
                    any_to_wav(file_path, wav_path)
                except Exception as e:  # 转换失败，直接使用mp3，对于某些api，mp3也可以识别
                    logger.warning("[chat_channel]any to wav error, use raw path. " + str(e))
                    wav_path = file_path
                # 语音识别
                from cow_platform.runtime.capabilities import activate_context_capability

                with activate_context_capability(context, "speech_to_text"):
                    reply = super().build_voice_to_text(wav_path)
                # 删除临时文件
                try:
                    os.remove(file_path)
                    if wav_path != file_path:
                        os.remove(wav_path)
                except Exception as e:
                    pass
                    # logger.warning("[chat_channel]delete temp file error: " + str(e))

                if reply.type == ReplyType.TEXT:
                    new_context = self._compose_context(ContextType.TEXT, reply.content, **context.kwargs)
                    if new_context:
                        reply = self._generate_reply(new_context)
                    else:
                        return
            elif context.type == ContextType.IMAGE:  # 图片消息，当前仅做下载保存到本地的逻辑
                memory.USER_IMAGE_CACHE[context["session_id"]] = {
                    "path": context.content,
                    "msg": context.get("msg")
                }
            elif context.type == ContextType.SHARING:  # 分享信息，当前无默认逻辑
                pass
            elif context.type == ContextType.FUNCTION or context.type == ContextType.FILE:  # 文件消息及函数调用等，当前无默认逻辑
                pass
            else:
                logger.warning("[chat_channel] unknown context type: {}".format(context.type))
                return
        return reply

    def _decorate_reply(self, context: Context, reply: Reply) -> Reply:
        if reply and reply.type:
            e_context = PluginManager().emit_event(
                EventContext(
                    Event.ON_DECORATE_REPLY,
                    {"channel": self, "context": context, "reply": reply},
                )
            )
            reply = e_context["reply"]
            desire_rtype = context.get("desire_rtype")
            if not e_context.is_pass() and reply and reply.type:
                if reply.type in self.NOT_SUPPORT_REPLYTYPE:
                    logger.error("[chat_channel]reply type not support: " + str(reply.type))
                    reply.type = ReplyType.ERROR
                    reply.content = "不支持发送的消息类型: " + str(reply.type)

                if reply.type == ReplyType.TEXT:
                    reply_text = reply.content
                    if desire_rtype == ReplyType.VOICE and ReplyType.VOICE not in self.NOT_SUPPORT_REPLYTYPE:
                        from cow_platform.runtime.capabilities import activate_context_capability

                        with activate_context_capability(context, "text_to_speech"):
                            reply = super().build_text_to_voice(reply.content)
                        return self._decorate_reply(context, reply)
                    if context.get("isgroup", False):
                        if not context.get("no_need_at", False):
                            reply_text = "@" + context["msg"].actual_user_nickname + "\n" + reply_text.strip()
                        reply_text = conf().get("group_chat_reply_prefix", "") + reply_text + conf().get("group_chat_reply_suffix", "")
                    else:
                        reply_text = conf().get("single_chat_reply_prefix", "") + reply_text + conf().get("single_chat_reply_suffix", "")
                    reply.content = reply_text
                elif reply.type == ReplyType.ERROR or reply.type == ReplyType.INFO:
                    reply.content = "[" + str(reply.type) + "]\n" + reply.content
                elif reply.type == ReplyType.IMAGE_URL or reply.type == ReplyType.VOICE or reply.type == ReplyType.IMAGE or reply.type == ReplyType.FILE or reply.type == ReplyType.VIDEO or reply.type == ReplyType.VIDEO_URL:
                    pass
                else:
                    logger.error("[chat_channel] unknown reply type: {}".format(reply.type))
                    return
            if desire_rtype and desire_rtype != reply.type and reply.type not in [ReplyType.ERROR, ReplyType.INFO]:
                logger.warning("[chat_channel] desire_rtype: {}, but reply type: {}".format(context.get("desire_rtype"), reply.type))
            return reply

    def _send_reply(self, context: Context, reply: Reply):
        if reply and reply.type:
            e_context = PluginManager().emit_event(
                EventContext(
                    Event.ON_SEND_REPLY,
                    {"channel": self, "context": context, "reply": reply},
                )
            )
            reply = e_context["reply"]
            if not e_context.is_pass() and reply and reply.type:
                logger.debug("[chat_channel] sending reply: {}, context: {}".format(reply, context))
                
                # 如果是文本回复，尝试提取并发送图片
                if reply.type == ReplyType.TEXT:
                    self._extract_and_send_images(reply, context)
                # 如果是图片回复但带有文本内容，先发文本再发图片
                elif reply.type == ReplyType.IMAGE_URL and hasattr(reply, 'text_content') and reply.text_content:
                    # 先发送文本
                    text_reply = Reply(ReplyType.TEXT, reply.text_content)
                    self._send(text_reply, context)
                    # 短暂延迟后发送图片
                    time.sleep(0.3)
                    self._send(reply, context)
                else:
                    self._send(reply, context)
    
    def _extract_and_send_images(self, reply: Reply, context: Context):
        """
        从文本回复中提取图片/视频URL并单独发送
        支持格式：[图片: /path/to/image.png], [视频: /path/to/video.mp4], ![](url), <img src="url">
        最多发送5个媒体文件
        """
        content = reply.content
        media_items = []  # [(url, type), ...]
        
        # 正则提取各种格式的媒体URL
        patterns = [
            (r'\[图片:\s*([^\]]+)\]', 'image'),   # [图片: /path/to/image.png]
            (r'\[视频:\s*([^\]]+)\]', 'video'),   # [视频: /path/to/video.mp4]
            (r'!\[.*?\]\(([^\)]+)\)', 'image'),   # ![alt](url) - 默认图片
            (r'<img[^>]+src=["\']([^"\']+)["\']', 'image'),  # <img src="url">
            (r'<video[^>]+src=["\']([^"\']+)["\']', 'video'),  # <video src="url">
            (r'https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp)', 'image'),  # 直接的图片URL
            (r'https?://[^\s]+\.(?:mp4|avi|mov|wmv|flv)', 'video'),  # 直接的视频URL
        ]
        
        for pattern, media_type in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                media_items.append((match, media_type))
        
        # 去重（保持顺序）并限制最多5个
        seen = set()
        unique_items = []
        for url, mtype in media_items:
            if url not in seen:
                seen.add(url)
                unique_items.append((url, mtype))
        media_items = unique_items[:5]
        
        if media_items:
            logger.info(f"[chat_channel] Extracted {len(media_items)} media item(s) from reply")
            
            # Send text first (the frontend will embed video players via renderMarkdown).
            logger.info(f"[chat_channel] Sending text content before media: {reply.content[:100]}...")
            self._send(reply, context)
            logger.info(f"[chat_channel] Text sent, now sending {len(media_items)} media item(s)")
            
            for i, (url, media_type) in enumerate(media_items):
                try:
                    # Determine whether it is a remote URL or a local file.
                    if url.startswith(('http://', 'https://')):
                        if media_type == 'video':
                            media_reply = Reply(ReplyType.FILE, url)
                            media_reply.file_name = os.path.basename(url)
                        else:
                            media_reply = Reply(ReplyType.IMAGE_URL, url)
                    elif os.path.exists(url):
                        if media_type == 'video':
                            media_reply = Reply(ReplyType.FILE, f"file://{url}")
                            media_reply.file_name = os.path.basename(url)
                        else:
                            media_reply = Reply(ReplyType.IMAGE_URL, f"file://{url}")
                    else:
                        logger.warning(f"[chat_channel] Media file not found or invalid URL: {url}")
                        continue
                    
                    if i > 0:
                        time.sleep(0.5)
                    self._send(media_reply, context)
                    logger.info(f"[chat_channel] Sent {media_type} {i+1}/{len(media_items)}: {url[:50]}...")
                    
                except Exception as e:
                    logger.error(f"[chat_channel] Failed to send {media_type} {url}: {e}")
        else:
            # 没有媒体文件，正常发送文本
                self._send(reply, context)

    def _send(self, reply: Reply, context: Context, retry_cnt=0):
        try:
            self.send(reply, context)
        except Exception as e:
            logger.error("[chat_channel] sendMsg error: {}".format(str(e)))
            if isinstance(e, NotImplementedError):
                return
            logger.exception(e)
            if retry_cnt < 2:
                time.sleep(3 + 3 * retry_cnt)
                self._send(reply, context, retry_cnt + 1)

    def _success_callback(self, session_id, **kwargs):  # 线程正常结束时的回调函数
        logger.debug("Worker return success, session_id = {}".format(session_id))

    def _fail_callback(self, session_id, exception, **kwargs):  # 线程异常结束时的回调函数
        logger.exception("Worker return exception: {}".format(exception))

    def _thread_pool_callback(self, session_id, **kwargs):
        def func(worker: Future):
            try:
                worker_exception = worker.exception()
                if worker_exception:
                    self._fail_callback(session_id, exception=worker_exception, **kwargs)
                else:
                    self._success_callback(session_id, **kwargs)
            except CancelledError as e:
                logger.info("Worker cancelled, session_id = {}".format(session_id))
            except Exception as e:
                logger.exception("Worker raise exception: {}".format(e))
            with self.lock:
                self.sessions[session_id][1].release()

        return func

    def produce(self, context: Context):
        session_id = context["session_id"]
        with self.lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = [
                    Dequeue(),
                    threading.BoundedSemaphore(conf().get("concurrency_in_session", 1)),
                ]
            if context.type == ContextType.TEXT and context.content.startswith("#"):
                self.sessions[session_id][0].putleft(context)  # 优先处理管理命令
            else:
                self.sessions[session_id][0].put(context)

            # Preemption: cancel any queued (not-yet-running) messages for this session
            # when a new user message arrives. Running tasks are cancelled cooperatively
            # via the CancelToken mechanism in agent_bridge.
            queue = self.sessions[session_id][0]
            if queue.qsize() > 1:
                # Remove all but the latest message from the queue
                items = []
                while not queue.empty():
                    try:
                        items.append(queue.get(block=False))
                    except Exception:
                        break
                # Keep only the last item (newest message)
                if items:
                    latest = items[-1]
                    dropped = len(items) - 1
                    if dropped > 0:
                        logger.info(
                            f"[chat_channel] Preemption: dropped {dropped} queued message(s) for session={session_id}"
                        )
                    queue.put(latest)

            # Preemption: also cancel the currently RUNNING agent task for this
            # session so it stops at the next cooperative yield point.  Without
            # this, the semaphore would block the new message until the old
            # handler finishes, making the CancelToken mechanism ineffective.
            try:
                Bridge().cancel_running_agent(self._cancel_session_key(context))
            except Exception:
                pass  # Agent bridge may not be initialised yet

    def _cancel_session_key(self, context: Context) -> str:
        session_id = context.get("session_id") or ""
        tenant_id = context.get("tenant_id") or ""
        agent_id = context.get("agent_id") or ""
        if tenant_id and agent_id and session_id:
            try:
                from cow_platform.runtime.namespaces import build_namespace

                return build_namespace(tenant_id, agent_id, session_id)
            except Exception:
                return session_id
        return session_id

    # 消费者函数，单独线程，用于从消息队列中取出消息并处理
    def consume(self):
        while True:
            with self.lock:
                session_ids = list(self.sessions.keys())
            for session_id in session_ids:
                with self.lock:
                    context_queue, semaphore = self.sessions[session_id]
                if semaphore.acquire(blocking=False):  # 等线程处理完毕才能删除
                    if not context_queue.empty():
                        context = context_queue.get()
                        logger.debug("[chat_channel] consume context: {}".format(context))
                        future: Future = handler_pool.submit(self._handle, context)
                        future.add_done_callback(self._thread_pool_callback(session_id, context=context))
                        with self.lock:
                            if session_id not in self.futures:
                                self.futures[session_id] = []
                            self.futures[session_id].append(future)
                    elif semaphore._initial_value == semaphore._value + 1:  # 除了当前，没有任务再申请到信号量，说明所有任务都处理完毕
                        with self.lock:
                            self.futures[session_id] = [t for t in self.futures[session_id] if not t.done()]
                            assert len(self.futures[session_id]) == 0, "thread pool error"
                            del self.sessions[session_id]
                    else:
                        semaphore.release()
            time.sleep(0.2)

    # 取消session_id对应的所有任务，只能取消排队的消息和已提交线程池但未执行的任务
    def cancel_session(self, session_id):
        with self.lock:
            if session_id in self.sessions:
                for future in self.futures[session_id]:
                    future.cancel()
                cnt = self.sessions[session_id][0].qsize()
                if cnt > 0:
                    logger.info("Cancel {} messages in session {}".format(cnt, session_id))
                self.sessions[session_id][0] = Dequeue()

    def cancel_all_session(self):
        with self.lock:
            for session_id in self.sessions:
                for future in self.futures[session_id]:
                    future.cancel()
                cnt = self.sessions[session_id][0].qsize()
                if cnt > 0:
                    logger.info("Cancel {} messages in session {}".format(cnt, session_id))
                self.sessions[session_id][0] = Dequeue()


def check_prefix(content, prefix_list):
    if not prefix_list:
        return None
    for prefix in prefix_list:
        if content.startswith(prefix):
            return prefix
    return None


def check_contain(content, keyword_list):
    if not keyword_list:
        return None
    for ky in keyword_list:
        if content.find(ky) != -1:
            return True
    return None
