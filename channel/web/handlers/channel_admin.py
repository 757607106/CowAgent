from __future__ import annotations

import json

import web

from common.log import logger
from channel.web.handlers.dependencies import (
    _get_channel_config_service,
    _require_auth,
    _require_tenant_manage,
    _restart_channel_config_runtime,
    _scope_tenant_id,
)

class ChannelsHandler:
    """Compatibility shell for the removed global-channel API.

    平台已经固定为多租户模式，渠道接入只能走租户级渠道配置。
    保留这个 route 是为了让旧前端或旧脚本拿到明确错误，而不是重新写 config.json 或启动全局渠道。
    """

    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            return json.dumps(
                {
                    "status": "success",
                    "channels": [],
                    "tenant_only": True,
                    "message": "多租户模式下渠道只通过租户级渠道配置管理",
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] Channels API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            _ = web.data()
            return json.dumps(
                {
                    "status": "error",
                    "message": "多租户模式不支持全局渠道操作，请使用租户级渠道配置",
                },
                ensure_ascii=False,
            )
        except Exception as e:
            logger.error(f"[WebChannel] Channels POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class WeixinQrHandler:
    """Handle WeChat QR code login from the web console.

    GET  /api/weixin/qrlogin          → fetch a new QR code
    POST /api/weixin/qrlogin          → poll QR status or start channel after login
    """

    _qr_state = {}

    @staticmethod
    def _qr_to_data_uri(data: str) -> str:
        """Generate a QR code as a PNG data URI."""
        try:
            import qrcode as qr_lib
            import io
            import base64
            qr = qr_lib.QRCode(error_correction=qr_lib.constants.ERROR_CORRECT_L, box_size=6, border=2)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return f"data:image/png;base64,{b64}"
        except ImportError:
            return ""

    @staticmethod
    def _state_key(channel_config_id: str = "") -> str:
        # 二维码状态必须绑定到租户渠道配置，避免恢复全局微信扫码会话。
        return (channel_config_id or "").strip()

    @staticmethod
    def _resolve_weixin_channel_config(channel_config_id: str):
        service = _get_channel_config_service()
        params = web.input(tenant_id='')
        tenant_id = _scope_tenant_id(params.tenant_id)
        definition = service.resolve_channel_config(
            tenant_id=tenant_id,
            channel_config_id=str(channel_config_id).strip(),
        )
        if definition.channel_type != "weixin":
            raise ValueError("channel config is not a weixin config")
        return service, definition, service.build_runtime_overrides(definition)

    def _fetch_qr(self, channel_config_id: str = ""):
        channel_config_id = str(channel_config_id or "").strip()
        if not channel_config_id:
            return json.dumps(
                {"status": "error", "message": "多租户模式请通过租户微信渠道配置扫码"},
                ensure_ascii=False,
            )
        _require_tenant_manage()
        _service, definition, overrides = self._resolve_weixin_channel_config(channel_config_id)
        base_url = str(overrides.get("weixin_base_url", "") or "")

        from channel.weixin.weixin_api import WeixinApi, DEFAULT_BASE_URL

        resolved_base_url = base_url or DEFAULT_BASE_URL
        api = WeixinApi(base_url=resolved_base_url)
        qr_resp = api.fetch_qr_code()
        qrcode = qr_resp.get("qrcode", "")
        qrcode_url = qr_resp.get("qrcode_img_content", "")
        if not qrcode:
            return json.dumps({"status": "error", "message": "No QR code returned"}, ensure_ascii=False)
        qr_image = self._qr_to_data_uri(qrcode_url)
        WeixinQrHandler._qr_state[self._state_key(channel_config_id)] = {
            "qrcode": qrcode,
            "qrcode_url": qrcode_url,
            "base_url": resolved_base_url,
            "channel_config_id": channel_config_id,
            "tenant_id": getattr(definition, "tenant_id", ""),
        }
        return json.dumps({
            "status": "success",
            "qrcode_url": qrcode_url,
            "qr_image": qr_image,
            "channel_config_id": channel_config_id,
        }, ensure_ascii=False)

    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(channel_config_id='')
            return self._fetch_qr(str(params.channel_config_id or "").strip())
        except Exception as e:
            logger.error(f"[WebChannel] WeixinQr GET error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data())
            action = body.get("action", "poll")
            channel_config_id = str(body.get("channel_config_id", "") or "").strip()

            if action == "poll":
                return self._poll_status(channel_config_id=channel_config_id)
            elif action == "refresh":
                return self._fetch_qr(channel_config_id)
            else:
                return json.dumps({"status": "error", "message": f"unknown action: {action}"})
        except Exception as e:
            logger.error(f"[WebChannel] WeixinQr POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def _poll_status(self, *, channel_config_id: str = ""):
        if not str(channel_config_id or "").strip():
            return json.dumps(
                {"status": "error", "message": "多租户模式请通过租户微信渠道配置扫码"},
                ensure_ascii=False,
            )
        state_key = self._state_key(channel_config_id)
        state = WeixinQrHandler._qr_state.get(state_key, {})
        qrcode = state.get("qrcode", "")
        base_url = state.get("base_url", "")
        if not qrcode:
            return json.dumps({"status": "error", "message": "No active QR session"})

        from channel.weixin.weixin_api import WeixinApi, DEFAULT_BASE_URL
        api = WeixinApi(base_url=base_url or DEFAULT_BASE_URL)
        try:
            status_resp = api.poll_qr_status(qrcode, timeout=10)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

        qr_status = status_resp.get("status", "wait")

        if qr_status == "confirmed":
            bot_token = status_resp.get("bot_token", "")
            bot_id = status_resp.get("ilink_bot_id", "")
            result_base_url = status_resp.get("baseurl", base_url)
            user_id = status_resp.get("ilink_user_id", "")

            if not bot_token or not bot_id:
                return json.dumps({"status": "error", "message": "Login confirmed but missing token"})

            service = _get_channel_config_service()
            definition = service.resolve_channel_config(
                tenant_id=str(state.get("tenant_id", "") or ""),
                channel_config_id=channel_config_id,
            )
            service.save_weixin_credentials(
                channel_config_id=definition.channel_config_id,
                tenant_id=definition.tenant_id,
                token=bot_token,
                base_url=result_base_url,
                bot_id=bot_id,
                user_id=user_id,
            )
            _restart_channel_config_runtime(definition.channel_config_id)

            WeixinQrHandler._qr_state.pop(state_key, None)
            logger.info(f"[WebChannel] WeChat QR login confirmed: bot_id={bot_id}")

            return json.dumps({
                "status": "success",
                "qr_status": "confirmed",
                "bot_id": bot_id,
                "channel_config_id": channel_config_id,
            })

        if qr_status == "expired":
            new_resp = api.fetch_qr_code()
            new_qrcode = new_resp.get("qrcode", "")
            new_qrcode_url = new_resp.get("qrcode_img_content", "")
            new_qr_image = self._qr_to_data_uri(new_qrcode_url)
            WeixinQrHandler._qr_state[state_key]["qrcode"] = new_qrcode
            WeixinQrHandler._qr_state[state_key]["qrcode_url"] = new_qrcode_url
            return json.dumps({
                "status": "success",
                "qr_status": "expired",
                "qrcode_url": new_qrcode_url,
                "qr_image": new_qr_image,
                "channel_config_id": channel_config_id,
            })

        return json.dumps({"status": "success", "qr_status": qr_status, "channel_config_id": channel_config_id})


__all__ = ["ChannelsHandler", "WeixinQrHandler"]
