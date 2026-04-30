"""
Background scheduler service for executing scheduled tasks
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional
from croniter import croniter
from common.log import logger


class SchedulerService:
    """
    Background service that executes scheduled tasks
    """
    
    def __init__(self, task_store, execute_callback: Callable):
        """
        Initialize scheduler service
        
        Args:
            task_store: TaskStore instance
            execute_callback: Function to call when executing a task
        """
        self.task_store = task_store
        self.execute_callback = execute_callback
        self.running = False
        self.thread = None
        self._lock = threading.Lock()
    
    def start(self):
        """Start the scheduler service"""
        with self._lock:
            if self.running:
                logger.warning("[Scheduler] Service already running")
                return
            
            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            logger.debug("[Scheduler] Service started")
    
    def stop(self):
        """Stop the scheduler service"""
        with self._lock:
            if not self.running:
                return
            
            self.running = False
            if self.thread:
                self.thread.join(timeout=5)
            logger.info("[Scheduler] Service stopped")
    
    def _run_loop(self):
        """Main scheduler loop"""
        logger.debug("[Scheduler] Scheduler loop started")
        
        while self.running:
            try:
                self._check_and_execute_tasks()
            except Exception as e:
                logger.error(f"[Scheduler] Error in scheduler loop: {e}")

            time.sleep(30)
    
    def _check_and_execute_tasks(self):
        """Check for due tasks and execute them"""
        now = datetime.now()
        tasks = self.task_store.list_tasks(enabled_only=True)
        
        for task in tasks:
            try:
                # Check if task is due
                if self._is_task_due(task, now):
                    logger.info(f"[Scheduler] Executing task: {task['id']} - {task['name']}")
                    outcome = self._execute_task(task)
                    
                    # Update next run time
                    next_run = self._calculate_next_run(task, now)
                    if next_run:
                        updates = {
                            "next_run_at": next_run.isoformat(),
                            "last_run_at": now.isoformat()
                        }
                        if outcome.get("status") == "failed":
                            updates["last_error"] = outcome.get("error", "")
                            updates["last_error_at"] = now.isoformat()
                        else:
                            updates["last_error"] = ""
                            updates["last_error_at"] = ""
                        self.task_store.update_task(task['id'], updates, task=task)
                    else:
                        # Keep completed one-time tasks for UI observability and run history.
                        updates = {
                            "enabled": False,
                            "next_run_at": "",
                            "last_run_at": now.isoformat(),
                        }
                        if outcome.get("status") == "failed":
                            updates["last_error"] = outcome.get("error", "")
                            updates["last_error_at"] = now.isoformat()
                        else:
                            updates["last_error"] = ""
                            updates["last_error_at"] = ""
                        self.task_store.update_task(task['id'], updates, task=task)
                        logger.info(f"[Scheduler] One-time task completed and retained: {task['id']}")
            except Exception as e:
                logger.error(f"[Scheduler] Error processing task {task.get('id')}: {e}")
    
    def _is_task_due(self, task: dict, now: datetime) -> bool:
        """
        Check if a task is due to run
        
        Args:
            task: Task dictionary
            now: Current datetime
            
        Returns:
            True if task should run now
        """
        next_run_str = task.get("next_run_at")
        if not next_run_str:
            # Calculate initial next_run_at
            next_run = self._calculate_next_run(task, now)
            if next_run:
                self.task_store.update_task(task['id'], {
                    "next_run_at": next_run.isoformat()
                }, task=task)
                return False
            return False
        
        try:
            next_run = datetime.fromisoformat(next_run_str)
            
            # Check if task is overdue (e.g., service restart)
            if next_run < now:
                time_diff = (now - next_run).total_seconds()
                
                # If overdue by more than 5 minutes, skip this run and schedule next
                if time_diff > 300:  # 5 minutes
                    logger.warning(f"[Scheduler] Task {task['id']} is overdue by {int(time_diff)}s, skipping and scheduling next run")
                    
                    # For one-time tasks, remove them directly
                    schedule = task.get("schedule", {})
                    if schedule.get("type") == "once":
                        self.task_store.update_task(task['id'], {
                            "enabled": False,
                            "next_run_at": "",
                            "last_error": "任务超过计划时间 5 分钟未执行，已自动停用",
                            "last_error_at": now.isoformat(),
                        }, task=task)
                        logger.info(f"[Scheduler] One-time task {task['id']} expired and disabled")
                        return False
                    
                    # For recurring tasks, calculate next run from now
                    next_next_run = self._calculate_next_run(task, now)
                    if next_next_run:
                        self.task_store.update_task(task['id'], {
                            "next_run_at": next_next_run.isoformat()
                        }, task=task)
                        logger.info(f"[Scheduler] Rescheduled task {task['id']} to {next_next_run}")
                    return False
            
            return now >= next_run
        except Exception:
            return False
    
    def _calculate_next_run(self, task: dict, from_time: datetime) -> Optional[datetime]:
        """
        Calculate next run time for a task
        
        Args:
            task: Task dictionary
            from_time: Calculate from this time
            
        Returns:
            Next run datetime or None for one-time tasks
        """
        schedule = task.get("schedule", {})
        schedule_type = schedule.get("type")
        
        if schedule_type == "cron":
            # Cron expression
            expression = schedule.get("expression")
            if not expression:
                return None
            
            try:
                cron = croniter(expression, from_time)
                return cron.get_next(datetime)
            except Exception as e:
                logger.error(f"[Scheduler] Invalid cron expression '{expression}': {e}")
                return None
        
        elif schedule_type == "interval":
            # Interval in seconds
            seconds = schedule.get("seconds", 0)
            if seconds <= 0:
                return None
            return from_time + timedelta(seconds=seconds)
        
        elif schedule_type == "once":
            # One-time task at specific time
            run_at_str = schedule.get("run_at")
            if not run_at_str:
                return None
            
            try:
                run_at = datetime.fromisoformat(run_at_str)
                # Only return if in the future
                if run_at > from_time:
                    return run_at
            except Exception:
                pass
            return None
        
        return None
    
    def execute_now(self, task: dict) -> dict:
        """Execute a task immediately without changing its configured schedule."""
        now = datetime.now()
        outcome = self._execute_task(task, trigger_type="manual")
        updates = {"last_run_at": now.isoformat()}
        if outcome.get("status") == "failed":
            updates["last_error"] = outcome.get("error", "")
            updates["last_error_at"] = now.isoformat()
        else:
            updates["last_error"] = ""
            updates["last_error_at"] = ""
        self.task_store.update_task(task["id"], updates, task=task)
        return outcome

    def _execute_task(self, task: dict, *, trigger_type: str = "schedule") -> dict:
        """
        Execute a task
        
        Args:
            task: Task dictionary
        """
        run_id = ""
        if hasattr(self.task_store, "add_task_run"):
            try:
                run = self.task_store.add_task_run(task, trigger_type=trigger_type)
                run_id = run.get("run_id", "")
            except Exception as e:
                logger.warning(f"[Scheduler] Failed to create task run record for {task['id']}: {e}")
        try:
            # Call the execute callback
            result = self.execute_callback(task)
            if hasattr(self.task_store, "finish_task_run") and run_id:
                self.task_store.finish_task_run(
                    run_id,
                    status="success",
                    result=result if isinstance(result, dict) else {"result": str(result or "")},
                )
            return {"status": "success", "run_id": run_id, "result": result or {}}
        except Exception as e:
            logger.error(f"[Scheduler] Error executing task {task['id']}: {e}")
            # Update task with error
            self.task_store.update_task(task['id'], {
                "last_error": str(e),
                "last_error_at": datetime.now().isoformat()
            }, task=task)
            if hasattr(self.task_store, "finish_task_run") and run_id:
                try:
                    self.task_store.finish_task_run(
                        run_id,
                        status="failed",
                        error_message=str(e),
                    )
                except Exception as record_error:
                    logger.warning(f"[Scheduler] Failed to finish task run record for {task['id']}: {record_error}")
            return {"status": "failed", "run_id": run_id, "error": str(e)}
