from __future__ import annotations

import os

from common.log import logger
from common.utils import expand_path
from config import conf


class LegacySchedulerRuntime:
    """Workspace JSON fallback for legacy CoreAgent scheduler tasks."""

    @staticmethod
    def create_task_store():
        from agent.tools.scheduler.task_store import TaskStore

        workspace_root = expand_path(conf().get("agent_workspace", "~/cow"))
        store_path = os.path.join(workspace_root, "scheduler", "tasks.json")
        logger.warning(f"[Scheduler] Using legacy JSON task store: {store_path}")
        return TaskStore(store_path)
