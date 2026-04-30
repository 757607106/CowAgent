from __future__ import annotations

from datetime import datetime, timedelta

from agent.tools.scheduler.scheduler_service import SchedulerService
from channel.web.handlers import workspace


class FakeRunStore:
    def __init__(self, task: dict):
        self.task = task
        self.runs: dict[str, dict] = {}
        self.updates: list[dict] = []

    def add_task_run(self, task: dict, *, trigger_type: str = "schedule", metadata=None) -> dict:
        run = {
            "run_id": f"run-{len(self.runs) + 1}",
            "task_id": task["id"],
            "trigger_type": trigger_type,
            "status": "running",
        }
        self.runs[run["run_id"]] = run
        return run

    def finish_task_run(self, run_id: str, *, status: str, result=None, error_message: str = "") -> bool:
        self.runs[run_id].update({
            "status": status,
            "result": result or {},
            "error_message": error_message,
        })
        return True

    def update_task(self, task_id: str, updates: dict, task=None) -> bool:
        self.updates.append(dict(updates))
        self.task.update(updates)
        return True


def make_task() -> dict:
    return {
        "id": "task-1",
        "tenant_id": "tenant-a",
        "agent_id": "agent-a",
        "name": "测试任务",
        "enabled": True,
        "schedule": {"type": "interval", "seconds": 60},
        "action": {"type": "send_message", "receiver": "session-a", "content": "hello"},
        "next_run_at": datetime.now().isoformat(),
    }


def test_scheduler_execute_now_records_success_run() -> None:
    task = make_task()
    store = FakeRunStore(task)
    service = SchedulerService(store, lambda current: {"sent": current["id"]})

    outcome = service.execute_now(task)

    assert outcome["status"] == "success"
    assert store.runs["run-1"]["trigger_type"] == "manual"
    assert store.runs["run-1"]["status"] == "success"
    assert store.runs["run-1"]["result"] == {"sent": "task-1"}
    assert store.task["last_error"] == ""
    assert store.task["last_error_at"] == ""


def test_scheduler_execute_now_records_failed_run() -> None:
    task = make_task()
    store = FakeRunStore(task)

    def fail(_task):
        raise RuntimeError("send failed")

    service = SchedulerService(store, fail)

    outcome = service.execute_now(task)

    assert outcome["status"] == "failed"
    assert store.runs["run-1"]["status"] == "failed"
    assert store.runs["run-1"]["error_message"] == "send failed"
    assert store.task["last_error"] == "send failed"
    assert store.task["last_error_at"]


def test_scheduler_api_builds_agent_task_payload_with_scope() -> None:
    run_at = (datetime.now() + timedelta(hours=1)).replace(microsecond=0).isoformat()
    task = workspace._build_scheduler_task(
        {
            "name": "日报",
            "action_type": "agent_task",
            "task_description": "生成日报",
            "receiver": "session-a",
            "receiver_name": "运营群",
            "channel_type": "web",
            "schedule_type": "once",
            "schedule_value": run_at,
        },
        {"tenant_id": "tenant-a", "agent_id": "agent-a", "binding_id": "binding-a"},
    )

    assert task["tenant_id"] == "tenant-a"
    assert task["agent_id"] == "agent-a"
    assert task["binding_id"] == "binding-a"
    assert task["action"]["type"] == "agent_task"
    assert task["action"]["task_description"] == "生成日报"
    assert task["schedule"] == {"type": "once", "run_at": run_at}
    assert task["next_run_at"]


def test_scheduler_api_respects_explicit_blank_channel_config() -> None:
    run_at = (datetime.now() + timedelta(hours=1)).replace(microsecond=0).isoformat()
    task = workspace._build_scheduler_task(
        {
            "name": "提醒",
            "action_type": "send_message",
            "content": "hello",
            "receiver": "session-a",
            "channel_type": "web",
            "channel_config_id": "",
            "schedule_type": "once",
            "schedule_value": run_at,
        },
        {
            "tenant_id": "tenant-a",
            "agent_id": "agent-a",
            "binding_id": "binding-a",
            "channel_config_id": "config-from-scope",
        },
    )

    assert task["channel_config_id"] == ""
    assert task["action"]["channel_config_id"] == ""


def test_scheduler_task_status_uses_enabled_error_and_completion() -> None:
    assert workspace._scheduler_task_status({"enabled": True, "next_run_at": "2026-01-01T00:00:00"}) == "scheduled"
    assert workspace._scheduler_task_status({"enabled": False}) == "disabled"
    assert workspace._scheduler_task_status({"enabled": True, "last_error": "boom"}) == "failed"
    assert workspace._scheduler_task_status({"enabled": False, "last_run_at": "2026-01-01T00:00:00", "last_error": "boom"}) == "failed"
    assert workspace._scheduler_task_status({"enabled": False, "last_run_at": "2026-01-01T00:00:00"}) == "completed"
