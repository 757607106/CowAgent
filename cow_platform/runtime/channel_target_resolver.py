from __future__ import annotations

from dataclasses import dataclass

from bridge.context import Context
from common.log import logger


@dataclass(frozen=True, slots=True)
class ChannelExternalIdentity:
    """External ids extracted from a channel message for binding resolution."""

    app_id: str = ""
    chat_id: str = ""
    user_id: str = ""

    @property
    def is_empty(self) -> bool:
        return not any((self.app_id, self.chat_id, self.user_id))


def _extract_external_identity(context: Context) -> ChannelExternalIdentity | None:
    cmsg = context.get("msg")
    if cmsg is None:
        return None
    return ChannelExternalIdentity(
        app_id=str(getattr(cmsg, "to_user_id", "") or "").strip(),
        chat_id=str(getattr(cmsg, "other_user_id", "") or "").strip(),
        user_id=str(
            getattr(cmsg, "actual_user_id", "") or getattr(cmsg, "from_user_id", "") or ""
        ).strip(),
    )


def resolve_channel_runtime_target(
    context: Context | None,
    *,
    channel_type: str,
    agent_enabled: bool,
) -> Context | None:
    """Resolve tenant/binding/agent target for managed non-web channel messages.

    ChatChannel owns message composition; platform runtime owns binding and tenant
    user lookup. Keeping the lookup here prevents channel classes from importing
    platform services directly.
    """
    if context is None or not agent_enabled:
        return context

    channel_config_id = str(context.get("channel_config_id", "") or "").strip()
    source_tenant_id = str(context.get("source_tenant_id", "") or "").strip()
    tenant_managed = bool(channel_config_id or source_tenant_id)
    if (
        not tenant_managed
        and (context.get("binding_id") or (context.get("tenant_id") and context.get("agent_id")))
    ):
        return context

    identity = _extract_external_identity(context)
    if identity is None:
        if tenant_managed:
            logger.warning(
                "[channel_target_resolver] managed channel context missing message metadata: "
                f"tenant={source_tenant_id}, channel_config_id={channel_config_id}"
            )
            return None
        return context

    if identity.is_empty:
        if tenant_managed:
            logger.warning(
                "[channel_target_resolver] managed channel context missing external identity: "
                f"tenant={source_tenant_id}, channel_config_id={channel_config_id}"
            )
            return None
        return context

    resolved_channel_type = context.get("channel_type", "") or channel_type
    try:
        from cow_platform.services.binding_service import ChannelBindingService

        binding = ChannelBindingService().resolve_binding_for_channel(
            channel_type=resolved_channel_type,
            channel_config_id=channel_config_id,
            external_app_id=identity.app_id,
            external_chat_id=identity.chat_id,
            external_user_id=identity.user_id,
        )
    except Exception as e:
        logger.warning(f"[channel_target_resolver] binding resolution failed: {e}")
        if tenant_managed:
            return None
        return context

    if binding is None:
        if tenant_managed:
            logger.warning(
                "[channel_target_resolver] no tenant binding matched for managed channel: "
                f"tenant={source_tenant_id}, channel_config_id={channel_config_id}, "
                f"channel_type={resolved_channel_type}, app={identity.app_id}, "
                f"chat={identity.chat_id}, user={identity.user_id}"
            )
            return None
        return context

    if source_tenant_id and binding.tenant_id != source_tenant_id:
        logger.error(
            "[channel_target_resolver] tenant binding mismatch for managed channel: "
            f"source_tenant={source_tenant_id}, binding_tenant={binding.tenant_id}, "
            f"binding_id={binding.binding_id}, channel_config_id={channel_config_id}"
        )
        return None

    context["binding_id"] = binding.binding_id
    context["tenant_id"] = binding.tenant_id
    context["agent_id"] = binding.agent_id
    context["binding_metadata"] = {
        "channel_config_id": context.get("channel_config_id", ""),
        "external_app_id": identity.app_id,
        "external_chat_id": identity.chat_id,
        "external_user_id": identity.user_id,
    }

    _attach_tenant_user_context(context, binding.tenant_id, resolved_channel_type, identity.user_id)
    return context


def _attach_tenant_user_context(
    context: Context,
    tenant_id: str,
    channel_type: str,
    external_user_id: str,
) -> None:
    if not external_user_id:
        return
    try:
        from cow_platform.services.tenant_user_service import TenantUserService

        tenant_user = TenantUserService().resolve_user_by_identity(
            tenant_id=tenant_id,
            channel_type=channel_type,
            external_user_id=external_user_id,
        )
        if tenant_user is None:
            return
        context["tenant_user_id"] = tenant_user.user_id
        context["tenant_user_role"] = tenant_user.role
        context["tenant_user_status"] = tenant_user.status
    except Exception as e:
        logger.warning(f"[channel_target_resolver] tenant user resolution failed: {e}")
