from __future__ import annotations

import json
import time

import web

from bridge.context import ContextType
from bridge.reply import ReplyType
from common.log import logger
from config import conf
from channel.web.handlers.dependencies import (
    _get_channel_config_service,
)

class WechatMpTenantCallbackHandler:
    def _resolve_channel(self, channel_config_id: str):
        from channel.wechatmp.wechatmp_channel import WechatMPChannel
        from cow_platform.runtime.scope import activate_config_overrides

        service = _get_channel_config_service()
        definition = service.resolve_channel_config(channel_config_id=str(channel_config_id).strip())
        if definition.channel_type not in {"wechatmp", "wechatmp_service"}:
            raise ValueError("channel config is not a wechatmp config")
        overrides = service.build_runtime_overrides(definition)
        with activate_config_overrides(overrides):
            channel = WechatMPChannel(
                passive_reply=definition.channel_type != "wechatmp_service",
                _singleton_key=definition.channel_config_id,
            )
        channel.channel_type = definition.channel_type
        channel.channel_config_id = definition.channel_config_id
        channel.tenant_id = definition.tenant_id
        channel.config_overrides = overrides
        return definition, overrides, channel

    def GET(self, channel_config_id):
        try:
            from wechatpy.exceptions import InvalidSignatureException
            from wechatpy.utils import check_signature

            _definition, overrides, _channel = self._resolve_channel(channel_config_id)
            data = web.input()
            try:
                check_signature(
                    str(overrides.get("wechatmp_token", "") or ""),
                    data.signature,
                    data.timestamp,
                    data.nonce,
                )
                return data.get("echostr", "")
            except InvalidSignatureException:
                raise web.Forbidden("Invalid signature")
        except web.HTTPError:
            raise
        except Exception as e:
            logger.warning(f"[WebChannel] WechatMP callback verify failed: {e}")
            raise web.Forbidden(str(e))

    def POST(self, channel_config_id):
        try:
            from wechatpy import parse_message
            from wechatpy.replies import create_reply
            from wechatpy.utils import check_signature

            from channel.wechatmp.wechatmp_message import WeChatMPMessage
            from common.utils import split_string_by_utf8_length
            from cow_platform.runtime.scope import activate_config_overrides

            _definition, overrides, channel = self._resolve_channel(channel_config_id)
            args = web.input()
            check_signature(
                str(overrides.get("wechatmp_token", "") or ""),
                args.signature,
                args.timestamp,
                args.nonce,
            )
            message = web.data()
            encrypt_func = lambda x: x
            if args.get("encrypt_type") == "aes":
                if not channel.crypto:
                    raise Exception("Crypto not initialized, Please set wechatmp_aes_key")
                message = channel.crypto.decrypt_message(message, args.msg_signature, args.timestamp, args.nonce)
                encrypt_func = lambda x: channel.crypto.encrypt_message(x, args.nonce, args.timestamp)
            msg = parse_message(message)
            if msg.type == "event":
                from config import subscribe_msg

                if msg.event in ["subscribe", "subscribe_scan"]:
                    reply_text = subscribe_msg()
                    if reply_text:
                        return encrypt_func(create_reply(reply_text, msg).render())
                return "success"
            if msg.type not in ["text", "voice", "image"]:
                return "success"

            with activate_config_overrides(overrides):
                wechatmp_msg = WeChatMPMessage(msg, client=channel.client)
                content = wechatmp_msg.content
                if msg.type == "voice" and wechatmp_msg.ctype == ContextType.TEXT and conf().get("voice_reply_voice", False):
                    context = channel._compose_context(
                        wechatmp_msg.ctype,
                        content,
                        isgroup=False,
                        desire_rtype=ReplyType.VOICE,
                        msg=wechatmp_msg,
                    )
                else:
                    context = channel._compose_context(wechatmp_msg.ctype, content, isgroup=False, msg=wechatmp_msg)
                if context:
                    if channel.passive_reply:
                        channel.running.add(wechatmp_msg.from_user_id)
                    channel.produce(context)

            if not channel.passive_reply:
                return "success"

            request_time = time.time()
            from_user = wechatmp_msg.from_user_id
            message_id = wechatmp_msg.msg_id
            channel.request_cnt[message_id] = channel.request_cnt.get(message_id, 0) + 1
            while time.time() < request_time + 4:
                if from_user in channel.running:
                    time.sleep(0.1)
                else:
                    break
            if from_user not in channel.cache_dict:
                return "success"
            try:
                reply_type, reply_content = channel.cache_dict[from_user].pop(0)
                if not channel.cache_dict[from_user]:
                    del channel.cache_dict[from_user]
            except IndexError:
                return "success"
            if reply_type == "text":
                max_len = 2048
                if len(reply_content.encode("utf8")) > max_len:
                    suffix = "\n【未完待续，回复任意文字以继续】"
                    reply_content = split_string_by_utf8_length(
                        reply_content,
                        max_len - len(suffix.encode("utf-8")),
                        max_split=1,
                    )[0] + suffix
                return encrypt_func(create_reply(reply_content, msg).render())
            return encrypt_func(create_reply("success", msg).render())
        except Exception as e:
            logger.exception(f"[WebChannel] WechatMP callback error: {e}")
            return "success"

class FeishuTenantCallbackHandler:
    def POST(self, channel_config_id):
        try:
            from channel.feishu.feishu_channel import FeiShuChanel, URL_VERIFICATION
            from cow_platform.runtime.scope import activate_config_overrides

            service = _get_channel_config_service()
            definition = service.resolve_channel_config(channel_config_id=str(channel_config_id).strip())
            if definition.channel_type != "feishu":
                raise ValueError("channel config is not a feishu config")
            overrides = service.build_runtime_overrides(definition)
            overrides["feishu_event_mode"] = "webhook"
            with activate_config_overrides(overrides):
                channel = FeiShuChanel(_singleton_key=definition.channel_config_id)
            channel.channel_type = definition.channel_type
            channel.channel_config_id = definition.channel_config_id
            channel.tenant_id = definition.tenant_id
            channel.config_overrides = overrides
            channel.feishu_app_id = str(overrides.get("feishu_app_id", "") or "")
            channel.feishu_app_secret = str(overrides.get("feishu_app_secret", "") or "")
            channel.feishu_token = str(overrides.get("feishu_token", "") or "")
            channel.feishu_event_mode = "webhook"

            request = json.loads(web.data().decode("utf-8"))
            if request.get("type") == URL_VERIFICATION:
                return json.dumps({"challenge": request.get("challenge")})
            header = request.get("header")
            if not header or header.get("token") != channel.feishu_token:
                return "failed"
            event = request.get("event")
            if event:
                channel._handle_message_event(event)
            return "success"
        except Exception as e:
            logger.exception(f"[WebChannel] Feishu callback error: {e}")
            return "failed"


__all__ = ["WechatMpTenantCallbackHandler", "FeishuTenantCallbackHandler"]
