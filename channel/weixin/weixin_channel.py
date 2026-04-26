"""
Weixin channel implementation.

Uses HTTP long-poll (getUpdates) to receive messages and sendMessage to reply.
Login token is supplied by the tenant channel config after web QR binding.
"""

import threading
import time
import uuid

import requests

from bridge.context import Context, ContextType
from bridge.reply import Reply, ReplyType
from channel.chat_channel import ChatChannel, check_prefix
from channel.weixin.weixin_api import (
    WeixinApi, upload_media_to_cdn,
    DEFAULT_BASE_URL, CDN_BASE_URL,
)
from channel.weixin.weixin_message import WeixinMessage
from common.expired_dict import ExpiredDict
from common.log import logger
from common.singleton import singleton
from config import conf

MAX_CONSECUTIVE_FAILURES = 3
BACKOFF_DELAY = 30
RETRY_DELAY = 2
SESSION_EXPIRED_ERRCODE = -14
TEXT_CHUNK_LIMIT = 4000


@singleton
class WeixinChannel(ChatChannel):

    LOGIN_STATUS_IDLE = "idle"
    LOGIN_STATUS_OK = "logged_in"

    def __init__(self):
        super().__init__()
        self.api = None
        self._stop_event = threading.Event()
        self._poll_thread = None
        self._context_tokens = {}  # user_id -> context_token
        self._received_msgs = ExpiredDict(60 * 60 * 7.1)
        self._get_updates_buf = ""
        self.login_status = self.LOGIN_STATUS_IDLE

        conf()["single_chat_prefix"] = [""]

    # ── Lifecycle ──────────────────────────────────────────────────────

    def startup(self):
        self._stop_event.clear()

        base_url = conf().get("weixin_base_url", DEFAULT_BASE_URL)
        cdn_base_url = conf().get("weixin_cdn_base_url", CDN_BASE_URL)
        token = conf().get("weixin_token", "")

        if not self.channel_config_id:
            logger.error("[Weixin] 平台多租户模式不支持全局微信通道，请通过租户渠道配置启动")
            return

        if not token:
            # 平台模式下微信 token 只能来自租户渠道配置数据库；旧本地 credentials 文件不再回退读取。
            logger.info(
                f"[Weixin] 租户微信渠道配置 {self.channel_config_id} 未绑定数据库凭证，请在渠道页面扫码绑定"
            )
            return

        self.api = WeixinApi(base_url=base_url, token=token, cdn_base_url=cdn_base_url)
        self.login_status = self.LOGIN_STATUS_OK

        logger.info(
            f"[Weixin] 微信通道已启动，凭证来自租户渠道配置数据库 "
            f"(channel_config_id={self.channel_config_id})，如需重新绑定请在渠道页面扫码登录或删除后重建"
        )
        self.report_startup_success()

        self._poll_loop()

    def stop(self):
        logger.info("[Weixin] stop() called")
        self._stop_event.set()

    def _relogin(self) -> bool:
        """Stop the tenant runtime after token expiry; rebinding is done only from the channel page."""
        logger.error(
            f"[Weixin] 租户微信渠道配置 {self.channel_config_id} 的登录已失效，"
            f"已清空数据库 token，请在渠道页面重新扫码绑定"
        )
        self._clear_tenant_credentials()
        self._stop_event.set()
        return False

    def _clear_tenant_credentials(self):
        if not self.channel_config_id:
            return
        try:
            from cow_platform.services.channel_config_service import ChannelConfigService

            ChannelConfigService().clear_weixin_credentials(
                channel_config_id=self.channel_config_id,
                tenant_id=self.tenant_id,
            )
        except Exception as exc:
            logger.warning(
                f"[Weixin] Failed to clear tenant weixin credentials "
                f"(channel_config_id={self.channel_config_id}): {exc}"
            )

    # ── Long-poll loop ─────────────────────────────────────────────────

    def _poll_loop(self):
        """Main long-poll loop: getUpdates -> parse -> produce."""
        logger.info("[Weixin] Starting long-poll loop")
        consecutive_failures = 0

        while not self._stop_event.is_set():
            try:
                resp = self.api.get_updates(self._get_updates_buf)

                ret = resp.get("ret", 0)
                errcode = resp.get("errcode", 0)

                is_error = (ret != 0) or (errcode != 0)
                if is_error:
                    if errcode == SESSION_EXPIRED_ERRCODE or ret == SESSION_EXPIRED_ERRCODE:
                        logger.error("[Weixin] Session expired (errcode -14), starting re-login...")
                        if self._relogin():
                            logger.info("[Weixin] Re-login successful, resuming long-poll")
                            self._get_updates_buf = ""
                            consecutive_failures = 0
                            continue
                        else:
                            logger.error("[Weixin] Re-login failed, will retry in 5 minutes")
                            self._stop_event.wait(300)
                            continue

                    consecutive_failures += 1
                    errmsg = resp.get("errmsg", "")
                    logger.error(f"[Weixin] getUpdates error: ret={ret} errcode={errcode} "
                                 f"errmsg={errmsg} ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})")
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        consecutive_failures = 0
                        self._stop_event.wait(BACKOFF_DELAY)
                    else:
                        self._stop_event.wait(RETRY_DELAY)
                    continue

                consecutive_failures = 0

                # Update sync cursor
                new_buf = resp.get("get_updates_buf", "")
                if new_buf:
                    self._get_updates_buf = new_buf

                # Process messages
                msgs = resp.get("msgs", [])
                for raw_msg in msgs:
                    try:
                        self._process_message(raw_msg)
                    except Exception as e:
                        logger.error(f"[Weixin] Failed to process message: {e}", exc_info=True)

            except Exception as e:
                if self._stop_event.is_set():
                    break
                consecutive_failures += 1
                logger.error(f"[Weixin] getUpdates exception: {e} "
                             f"({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})")
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    consecutive_failures = 0
                    self._stop_event.wait(BACKOFF_DELAY)
                else:
                    self._stop_event.wait(RETRY_DELAY)

        logger.info("[Weixin] Long-poll loop ended")

    def _process_message(self, raw_msg: dict):
        """Parse a single inbound message and produce to the handling queue."""
        msg_type = raw_msg.get("message_type", 0)
        if msg_type != 1:  # Only process USER messages (type=1)
            return

        msg_id = str(raw_msg.get("message_id", raw_msg.get("seq", "")))
        if self._received_msgs.get(msg_id):
            return
        self._received_msgs[msg_id] = True

        from_user = raw_msg.get("from_user_id", "")
        context_token = raw_msg.get("context_token", "")

        if context_token and from_user:
            self._context_tokens[from_user] = context_token

        cdn_base_url = self.api.cdn_base_url if self.api else CDN_BASE_URL
        try:
            wx_msg = WeixinMessage(raw_msg, cdn_base_url=cdn_base_url)
        except Exception as e:
            logger.error(f"[Weixin] Failed to parse WeixinMessage: {e}", exc_info=True)
            return

        logger.info(f"[Weixin] Received: from={from_user} ctype={wx_msg.ctype} "
                     f"content={str(wx_msg.content)[:50]}")

        # File cache logic
        from channel.file_cache import get_file_cache
        file_cache = get_file_cache()
        session_id = from_user

        if wx_msg.ctype == ContextType.IMAGE:
            if hasattr(wx_msg, "image_path") and wx_msg.image_path:
                file_cache.add(session_id, wx_msg.image_path, file_type="image")
                logger.info(f"[Weixin] Image cached for session {session_id}")
            return

        if wx_msg.ctype == ContextType.FILE:
            wx_msg.prepare()
            file_cache.add(session_id, wx_msg.content, file_type="file")
            logger.info(f"[Weixin] File cached for session {session_id}: {wx_msg.content}")
            return

        if wx_msg.ctype == ContextType.TEXT:
            cached_files = file_cache.get(session_id)
            if cached_files:
                refs = []
                for fi in cached_files:
                    ftype, fpath = fi["type"], fi["path"]
                    if ftype == "image":
                        refs.append(f"[图片: {fpath}]")
                    elif ftype == "video":
                        refs.append(f"[视频: {fpath}]")
                    else:
                        refs.append(f"[文件: {fpath}]")
                wx_msg.content = wx_msg.content + "\n" + "\n".join(refs)
                file_cache.clear(session_id)

        context = self._compose_context(
            wx_msg.ctype,
            wx_msg.content,
            isgroup=False,
            msg=wx_msg,
            no_need_at=True,
        )
        if context:
            self.produce(context)

    # ── _compose_context ───────────────────────────────────────────────

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

        cmsg = context["msg"]
        context["session_id"] = cmsg.from_user_id
        context["receiver"] = cmsg.other_user_id

        if ctype == ContextType.TEXT:
            img_match_prefix = check_prefix(content, conf().get("image_create_prefix"))
            if img_match_prefix:
                content = content.replace(img_match_prefix, "", 1)
                context.type = ContextType.IMAGE_CREATE
            else:
                context.type = ContextType.TEXT
            context.content = content.strip()

        return self._apply_platform_runtime_target(context)

    # ── Send reply ─────────────────────────────────────────────────────

    def send(self, reply: Reply, context: Context):
        receiver = context.get("receiver", "")
        msg = context.get("msg")
        context_token = self._get_context_token(receiver, msg)

        if not context_token:
            logger.error(f"[Weixin] No context_token for receiver={receiver}, cannot send")
            return

        if reply.type == ReplyType.TEXT:
            self._send_text(reply.content, receiver, context_token)
        elif reply.type in (ReplyType.IMAGE_URL, ReplyType.IMAGE):
            self._send_image(reply.content, receiver, context_token)
        elif reply.type == ReplyType.FILE:
            self._send_file(reply.content, receiver, context_token)
        elif reply.type in (ReplyType.VIDEO, ReplyType.VIDEO_URL):
            self._send_video(reply.content, receiver, context_token)
        else:
            logger.warning(f"[Weixin] Unsupported reply type: {reply.type}, fallback to text")
            self._send_text(str(reply.content), receiver, context_token)

    def _get_context_token(self, receiver: str, msg=None) -> str:
        """Get the context_token for a receiver, required for all sends."""
        if msg and hasattr(msg, "context_token") and msg.context_token:
            return msg.context_token
        return self._context_tokens.get(receiver, "")

    def _send_text(self, text: str, receiver: str, context_token: str):
        if len(text) <= TEXT_CHUNK_LIMIT:
            try:
                self.api.send_text(receiver, text, context_token)
                logger.debug(f"[Weixin] Text sent to {receiver}, len={len(text)}")
            except Exception as e:
                logger.error(f"[Weixin] Failed to send text: {e}")
            return

        chunks = self._split_text(text, TEXT_CHUNK_LIMIT)
        for i, chunk in enumerate(chunks):
            try:
                self.api.send_text(receiver, chunk, context_token)
                logger.debug(f"[Weixin] Text chunk {i+1}/{len(chunks)} sent to {receiver}, len={len(chunk)}")
            except Exception as e:
                logger.error(f"[Weixin] Failed to send text chunk {i+1}/{len(chunks)}: {e}")
                break
            if i < len(chunks) - 1:
                time.sleep(0.5)

    @staticmethod
    def _split_text(text: str, limit: int) -> list:
        """Split text into chunks, preferring to break at paragraph or line boundaries."""
        if len(text) <= limit:
            return [text]
        chunks = []
        while text:
            if len(text) <= limit:
                chunks.append(text)
                break
            cut = text.rfind("\n\n", 0, limit)
            if cut <= 0:
                cut = text.rfind("\n", 0, limit)
            if cut <= 0:
                cut = limit
            chunks.append(text[:cut])
            text = text[cut:].lstrip("\n")
        return chunks

    def _send_image(self, img_path_or_url: str, receiver: str, context_token: str):
        local_path = self._resolve_media_path(img_path_or_url)
        if not local_path:
            self._send_text("[Image send failed: file not found]", receiver, context_token)
            return
        try:
            result = upload_media_to_cdn(self.api, local_path, receiver, media_type=1)
            self.api.send_image_item(
                to=receiver,
                context_token=context_token,
                encrypt_query_param=result["encrypt_query_param"],
                aes_key_b64=result["aes_key_b64"],
                ciphertext_size=result["ciphertext_size"],
            )
            logger.info(f"[Weixin] Image sent to {receiver}")
        except Exception as e:
            logger.error(f"[Weixin] Image send failed: {e}")
            self._send_text("[Image send failed]", receiver, context_token)

    def _send_file(self, file_path_or_url: str, receiver: str, context_token: str):
        local_path = self._resolve_media_path(file_path_or_url)
        if not local_path:
            self._send_text("[File send failed: file not found]", receiver, context_token)
            return
        try:
            result = upload_media_to_cdn(self.api, local_path, receiver, media_type=3)
            self.api.send_file_item(
                to=receiver,
                context_token=context_token,
                encrypt_query_param=result["encrypt_query_param"],
                aes_key_b64=result["aes_key_b64"],
                file_name=os.path.basename(local_path),
                file_size=result["raw_size"],
            )
            logger.info(f"[Weixin] File sent to {receiver}")
        except Exception as e:
            logger.error(f"[Weixin] File send failed: {e}")
            self._send_text("[File send failed]", receiver, context_token)

    def _send_video(self, video_path_or_url: str, receiver: str, context_token: str):
        local_path = self._resolve_media_path(video_path_or_url)
        if not local_path:
            self._send_text("[Video send failed: file not found]", receiver, context_token)
            return
        try:
            result = upload_media_to_cdn(self.api, local_path, receiver, media_type=2)
            self.api.send_video_item(
                to=receiver,
                context_token=context_token,
                encrypt_query_param=result["encrypt_query_param"],
                aes_key_b64=result["aes_key_b64"],
                ciphertext_size=result["ciphertext_size"],
            )
            logger.info(f"[Weixin] Video sent to {receiver}")
        except Exception as e:
            logger.error(f"[Weixin] Video send failed: {e}")
            self._send_text("[Video send failed]", receiver, context_token)

    @staticmethod
    def _resolve_media_path(path_or_url: str) -> str:
        """Resolve a file path or URL to a local file path. Downloads if needed."""
        if not path_or_url:
            return ""

        local_path = path_or_url
        if local_path.startswith("file://"):
            local_path = local_path[7:]

        if local_path.startswith(("http://", "https://")):
            try:
                resp = requests.get(local_path, timeout=60)
                resp.raise_for_status()
                ct = resp.headers.get("Content-Type", "")
                ext = ".bin"
                if "jpeg" in ct or "jpg" in ct:
                    ext = ".jpg"
                elif "png" in ct:
                    ext = ".png"
                elif "gif" in ct:
                    ext = ".gif"
                elif "webp" in ct:
                    ext = ".webp"
                elif "mp4" in ct:
                    ext = ".mp4"
                elif "pdf" in ct:
                    ext = ".pdf"

                tmp_path = f"/tmp/wx_media_{uuid.uuid4().hex[:8]}{ext}"
                with open(tmp_path, "wb") as f:
                    f.write(resp.content)
                return tmp_path
            except Exception as e:
                logger.error(f"[Weixin] Failed to download media: {e}")
                return ""

        if os.path.exists(local_path):
            return local_path

        logger.warning(f"[Weixin] Media file not found: {local_path}")
        return ""
