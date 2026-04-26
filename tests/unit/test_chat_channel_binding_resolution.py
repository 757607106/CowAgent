from bridge.context import Context, ContextType
from channel.terminal.terminal_channel import TerminalChannel, TerminalMessage
from config import conf
from cow_platform.services.agent_service import AgentService
from cow_platform.services.binding_service import ChannelBindingService
from cow_platform.services.tenant_service import TenantService
from cow_platform.services.tenant_user_service import TenantUserService
from tests.support.platform_fakes import (
    EmptyPlatformUserService,
    InMemoryAgentRepository,
    InMemoryBindingRepository,
    InMemoryTenantRepository,
    InMemoryTenantUserRepository,
)


def test_chat_channel_injects_platform_binding_target(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent_workspace", str(tmp_path / "legacy"))
    monkeypatch.setitem(conf(), "model", "legacy-model")
    monkeypatch.setitem(conf(), "agent", True)
    monkeypatch.setitem(conf(), "single_chat_prefix", [""])
    monkeypatch.setitem(conf(), "image_create_prefix", [])

    tenant_service = TenantService(repository=InMemoryTenantRepository())
    agent_service = AgentService(
        repository=InMemoryAgentRepository(tmp_path / "legacy"),
        tenant_service=tenant_service,
    )
    binding_service = ChannelBindingService(
        repository=InMemoryBindingRepository(),
        tenant_service=tenant_service,
        agent_service=agent_service,
    )
    tenant_user_service = TenantUserService(
        repository=InMemoryTenantUserRepository(),
        tenant_service=tenant_service,
        platform_user_service=EmptyPlatformUserService(),
    )

    tenant_service.create_tenant(tenant_id="acme", name="Acme")
    agent_service.create_agent(
        tenant_id="acme",
        agent_id="support",
        name="客服助手",
        model="qwen-plus",
        system_prompt="你负责客服。",
    )
    binding_service.create_binding(
        tenant_id="acme",
        binding_id="terminal-support",
        name="终端客服入口",
        channel_type="terminal",
        agent_id="support",
        metadata={
            "external_app_id": "terminal-app",
            "external_chat_id": "terminal-chat",
            "external_user_id": "user-42",
        },
    )
    tenant_user_service.create_user(
        tenant_id="acme",
        user_id="alice",
        name="Alice",
        role="owner",
        status="active",
    )
    tenant_user_service.bind_identity(
        tenant_id="acme",
        user_id="alice",
        channel_type="terminal",
        external_user_id="user-42",
    )
    monkeypatch.setattr(
        "cow_platform.services.binding_service.ChannelBindingService",
        lambda: binding_service,
    )
    monkeypatch.setattr(
        "cow_platform.services.tenant_user_service.TenantUserService",
        lambda: tenant_user_service,
    )

    channel = TerminalChannel()
    channel.channel_type = "terminal"
    msg = TerminalMessage(
        1,
        "hello",
        from_user_id="user-42",
        to_user_id="terminal-app",
        other_user_id="terminal-chat",
    )

    context = channel._compose_context(ContextType.TEXT, "hello", msg=msg, isgroup=False)

    assert context is not None
    assert context["binding_id"] == "terminal-support"
    assert context["tenant_id"] == "acme"
    assert context["agent_id"] == "support"
    assert context["tenant_user_id"] == "alice"
    assert context["tenant_user_role"] == "owner"
    assert context["tenant_user_status"] == "active"


def test_context_kwargs_are_not_shared_between_messages() -> None:
    first = Context(ContextType.TEXT, "first")
    first["tenant_id"] = "psl-tenant"
    first["agent_id"] = "agt_17f2b502"
    first["binding_id"] = "bind_c49323e4"

    second = Context(ContextType.TEXT, "second")

    assert first.kwargs is not second.kwargs
    assert second.get("tenant_id") is None
    assert second.get("agent_id") is None
    assert second.get("binding_id") is None


def test_managed_channel_without_binding_fails_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.setitem(conf(), "agent", True)
    monkeypatch.setitem(conf(), "single_chat_prefix", [""])
    monkeypatch.setitem(conf(), "image_create_prefix", [])

    binding_service = ChannelBindingService(
        repository=InMemoryBindingRepository(),
        tenant_service=TenantService(repository=InMemoryTenantRepository()),
        agent_service=AgentService(repository=InMemoryAgentRepository(tmp_path / "legacy")),
    )
    monkeypatch.setattr(
        "cow_platform.services.binding_service.ChannelBindingService",
        lambda: binding_service,
    )

    channel = TerminalChannel()
    channel.channel_type = "weixin"
    channel.channel_config_id = "tenant-a-weixin"
    channel.tenant_id = "tenant-a"
    msg = TerminalMessage(
        1,
        "hello",
        from_user_id="user-42",
        to_user_id="weixin-bot",
        other_user_id="user-42",
    )

    context = channel._compose_context(
        ContextType.TEXT,
        "hello",
        msg=msg,
        isgroup=False,
        tenant_id="stale-tenant",
        agent_id="stale-agent",
        binding_id="stale-binding",
    )

    assert context is None
