from bridge.context import Context, ContextType
from channel.chat_channel import ChatChannel
from cow_platform.runtime.namespaces import build_namespace
from cow_platform.services.scheduler_task_store import PlatformSchedulerTaskStore
from agent.tools.scheduler.scheduler_tool import SchedulerTool


class FakeScopedStore:
    def __init__(self):
        self.context = None
        self.tasks = []

    def for_context(self, context):
        self.context = context
        return self

    def add_task(self, task):
        self.tasks.append(task)
        return True


def test_scheduler_tool_persists_platform_scope_in_task():
    context = Context(ContextType.TEXT, "remind me")
    context["tenant_id"] = "tenant-a"
    context["agent_id"] = "agent-a"
    context["binding_id"] = "binding-a"
    context["channel_config_id"] = "channel-a"
    context["channel_type"] = "web"
    context["session_id"] = "session-a"
    context["receiver"] = "user-a"
    context["isgroup"] = False

    store = FakeScopedStore()
    tool = SchedulerTool()
    tool.task_store = store
    tool.current_context = context

    result = tool.execute(
        {
            "action": "create",
            "name": "daily report",
            "message": "send report",
            "schedule_type": "once",
            "schedule_value": "+1m",
        }
    )

    assert result.status == "success"
    assert len(store.tasks) == 1
    task = store.tasks[0]
    assert task["tenant_id"] == "tenant-a"
    assert task["agent_id"] == "agent-a"
    assert task["binding_id"] == "binding-a"
    assert task["channel_config_id"] == "channel-a"
    assert task["session_id"] == "session-a"
    assert task["action"]["tenant_id"] == "tenant-a"
    assert task["action"]["agent_id"] == "agent-a"


def test_platform_scheduler_store_scopes_from_context():
    context = Context(ContextType.TEXT, "list tasks")
    context["tenant_id"] = "tenant-b"
    context["agent_id"] = "agent-b"
    context["binding_id"] = "binding-b"
    context["channel_config_id"] = "channel-b"
    context["session_id"] = "session-b"

    store = PlatformSchedulerTaskStore().for_context(context)

    assert store.tenant_id == "tenant-b"
    assert store.agent_id == "agent-b"
    assert store.binding_id == "binding-b"
    assert store.channel_config_id == "channel-b"
    assert store.session_id == "session-b"


def test_chat_channel_cancel_key_is_tenant_agent_scoped():
    context = Context(ContextType.TEXT, "new message")
    context["tenant_id"] = "tenant-c"
    context["agent_id"] = "agent-c"
    context["session_id"] = "session-c"

    key = ChatChannel._cancel_session_key(object(), context)

    assert key == build_namespace("tenant-c", "agent-c", "session-c")
