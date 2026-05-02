from __future__ import annotations

from bridge.context import Context
from bridge.reply import Reply
from common.log import logger


class PlatformSchedulerRuntime:
    """Platform-specific scheduler storage and channel dispatch boundary."""

    @staticmethod
    def create_task_store():
        from cow_platform.db import connect
        from cow_platform.services.scheduler_task_store import PlatformSchedulerTaskStore

        with connect() as conn:
            conn.execute("SELECT 1").fetchone()
        logger.info("[Scheduler] Using platform DB task store")
        return PlatformSchedulerTaskStore()

    @staticmethod
    def task_scope(task: dict) -> dict[str, str]:
        action = task.get("action", {}) if isinstance(task.get("action"), dict) else {}
        return {
            "tenant_id": str(task.get("tenant_id") or action.get("tenant_id") or ""),
            "agent_id": str(task.get("agent_id") or action.get("agent_id") or ""),
            "binding_id": str(task.get("binding_id") or action.get("binding_id") or ""),
            "channel_config_id": str(task.get("channel_config_id") or action.get("channel_config_id") or ""),
            "channel_type": str(action.get("channel_type") or task.get("channel_type") or ""),
        }

    def apply_task_scope(self, context: Context, task: dict) -> None:
        for key, value in self.task_scope(task).items():
            if value:
                context[key] = value

    def channel_runtime_overrides(self, task: dict) -> dict:
        channel_config_id = self.task_scope(task).get("channel_config_id", "")
        if not channel_config_id:
            return {}
        try:
            from cow_platform.services.channel_config_service import ChannelConfigService

            service = ChannelConfigService()
            definition = service.resolve_channel_config(channel_config_id=channel_config_id)
            return service.build_runtime_overrides(definition)
        except Exception as e:
            logger.warning(
                f"[Scheduler] Failed to resolve channel runtime overrides for {channel_config_id}: {e}"
            )
            return {}

    def send_reply_via_channel(
        self,
        channel_type: str,
        reply: Reply,
        context: Context,
        task: dict,
    ) -> bool:
        from channel.channel_factory import create_channel
        from cow_platform.runtime.scope import activate_config_overrides

        scope = self.task_scope(task)
        channel_config_id = scope.get("channel_config_id", "")
        overrides = self.channel_runtime_overrides(task)
        with activate_config_overrides(overrides):
            channel = create_channel(channel_type, singleton_key=channel_config_id)
            if channel_config_id:
                setattr(channel, "channel_config_id", channel_config_id)
            if scope.get("tenant_id"):
                setattr(channel, "tenant_id", scope["tenant_id"])
            if channel_type == "web" and hasattr(channel, "request_to_session"):
                request_id = context.get("request_id")
                receiver = context.get("receiver")
                if request_id and receiver:
                    channel.request_to_session[request_id] = receiver
                    logger.debug(f"[Scheduler] Registered request_id {request_id} -> session {receiver}")
            channel.send(reply, context)
        return True
