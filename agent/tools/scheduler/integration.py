"""
Integration module for scheduler with AgentBridge
"""

import os
from typing import Optional
from config import conf
from common.log import logger
from common.utils import expand_path
from bridge.context import Context, ContextType
from bridge.reply import Reply, ReplyType

# Global scheduler service instance
_scheduler_service = None
_task_store = None


def _create_task_store():
    """Use PostgreSQL as scheduler source of truth when platform DB is available."""
    try:
        from cow_platform.db import connect
        from cow_platform.services.scheduler_task_store import PlatformSchedulerTaskStore

        with connect() as conn:
            conn.execute("SELECT 1").fetchone()
        logger.info("[Scheduler] Using platform DB task store")
        return PlatformSchedulerTaskStore()
    except Exception as e:
        logger.warning(f"[Scheduler] Platform DB task store unavailable, falling back to workspace JSON: {e}")

    from agent.tools.scheduler.task_store import TaskStore

    workspace_root = expand_path(conf().get("agent_workspace", "~/cow"))
    store_path = os.path.join(workspace_root, "scheduler", "tasks.json")
    logger.warning(f"[Scheduler] Using legacy JSON task store: {store_path}")
    return TaskStore(store_path)


def init_scheduler(agent_bridge) -> bool:
    """
    Initialize scheduler service
    
    Args:
        agent_bridge: AgentBridge instance
        
    Returns:
        True if initialized successfully
    """
    global _scheduler_service, _task_store
    
    try:
        from agent.tools.scheduler.scheduler_service import SchedulerService

        _task_store = _create_task_store()
        
        # Create execute callback
        def execute_task_callback(task: dict):
            """Callback to execute a scheduled task"""
            try:
                action = task.get("action", {})
                action_type = action.get("type")
                
                if action_type == "agent_task":
                    _execute_agent_task(task, agent_bridge)
                elif action_type == "send_message":
                    # Legacy support for old tasks
                    _execute_send_message(task, agent_bridge)
                elif action_type == "tool_call":
                    # Legacy support for old tasks
                    _execute_tool_call(task, agent_bridge)
                elif action_type == "skill_call":
                    # Legacy support for old tasks
                    _execute_skill_call(task, agent_bridge)
                else:
                    raise RuntimeError(f"unknown action type: {action_type}")
            except Exception as e:
                logger.error(f"[Scheduler] Error executing task {task.get('id')}: {e}")
                raise
        
        # Create scheduler service
        _scheduler_service = SchedulerService(_task_store, execute_task_callback)
        _scheduler_service.start()
        
        logger.debug("[Scheduler] Scheduler service initialized and started")
        return True
        
    except Exception as e:
        logger.error(f"[Scheduler] Failed to initialize scheduler: {e}")
        return False


def get_task_store():
    """Get the global task store instance"""
    return _task_store


def get_scheduler_service():
    """Get the global scheduler service instance"""
    return _scheduler_service


def _execute_agent_task(task: dict, agent_bridge):
    """
    Execute an agent_task action - let Agent handle the task
    
    Args:
        task: Task dictionary
        agent_bridge: AgentBridge instance
    """
    try:
        action = task.get("action", {})
        task_description = action.get("task_description")
        receiver = action.get("receiver")
        is_group = action.get("is_group", False)
        channel_type = action.get("channel_type", "unknown")
        
        if not task_description:
            raise RuntimeError("No task_description specified")
        
        if not receiver:
            raise RuntimeError("No receiver specified")
        
        # Check for unsupported channels
        if channel_type == "dingtalk":
            logger.warning(f"[Scheduler] Task {task['id']}: DingTalk channel does not support scheduled messages (Stream mode limitation). Task will execute but message cannot be sent.")
        
        logger.info(f"[Scheduler] Task {task['id']}: Executing agent task '{task_description}'")
        
        # Create a unique session_id for this scheduled task to avoid polluting user's conversation
        # Format: scheduler_<receiver>_<task_id> to ensure isolation
        scheduler_session_id = f"scheduler_{receiver}_{task['id']}"
        
        # Create context for Agent
        context = Context(ContextType.TEXT, task_description)
        context["receiver"] = receiver
        context["isgroup"] = is_group
        context["session_id"] = scheduler_session_id
        _apply_task_scope(context, task)
        
        # Channel-specific setup
        if channel_type == "web":
            import uuid
            request_id = f"scheduler_{task['id']}_{uuid.uuid4().hex[:8]}"
            context["request_id"] = request_id
        elif channel_type == "feishu":
            context["receive_id_type"] = "chat_id" if is_group else "open_id"
            context["msg"] = None
        elif channel_type == "dingtalk":
            # DingTalk requires msg object, set to None for scheduled tasks
            context["msg"] = None
            if not is_group:
                sender_staff_id = action.get("dingtalk_sender_staff_id")
                if sender_staff_id:
                    context["dingtalk_sender_staff_id"] = sender_staff_id
        elif channel_type == "wecom_bot":
            context["msg"] = None

        # Use Agent to execute the task
        # Mark this as a scheduled task execution to prevent recursive task creation
        context["is_scheduled_task"] = True
        
        try:
            # Don't clear history - scheduler tasks use isolated session_id so they won't pollute user conversations
            reply = agent_bridge.agent_reply(task_description, context=context, on_event=None, clear_history=False)
            
            if reply and reply.content:
                # Send the reply via channel
                try:
                    if _send_reply_via_channel(channel_type, reply, context, task):
                        logger.info(f"[Scheduler] Task {task['id']} executed successfully, result sent to {receiver}")
                    else:
                        raise RuntimeError("send result returned false")
                except Exception as e:
                    logger.error(f"[Scheduler] Failed to send result: {e}")
                    raise
            else:
                raise RuntimeError("No result from agent execution")
                
        except Exception as e:
            logger.error(f"[Scheduler] Failed to execute task via Agent: {e}")
            import traceback
            logger.error(f"[Scheduler] Traceback: {traceback.format_exc()}")
            raise
            
    except Exception as e:
        logger.error(f"[Scheduler] Error in _execute_agent_task: {e}")
        import traceback
        logger.error(f"[Scheduler] Traceback: {traceback.format_exc()}")
        raise


def _execute_send_message(task: dict, agent_bridge):
    """
    Execute a send_message action
    
    Args:
        task: Task dictionary
        agent_bridge: AgentBridge instance
    """
    try:
        action = task.get("action", {})
        content = action.get("content", "")
        receiver = action.get("receiver")
        is_group = action.get("is_group", False)
        channel_type = action.get("channel_type", "unknown")
        
        if not receiver:
            raise RuntimeError("No receiver specified")
        
        # Create context for sending message
        context = Context(ContextType.TEXT, content)
        context["receiver"] = receiver
        context["isgroup"] = is_group
        context["session_id"] = receiver
        _apply_task_scope(context, task)
        
        # Channel-specific context setup
        if channel_type == "web":
            # Web channel needs request_id
            import uuid
            request_id = f"scheduler_{task['id']}_{uuid.uuid4().hex[:8]}"
            context["request_id"] = request_id
            logger.debug(f"[Scheduler] Generated request_id for web channel: {request_id}")
        elif channel_type == "feishu":
            # Feishu channel: for scheduled tasks, send as new message (no msg_id to reply to)
            # Use chat_id for groups, open_id for private chats
            context["receive_id_type"] = "chat_id" if is_group else "open_id"
            # Keep isgroup as is, but set msg to None (no original message to reply to)
            # Feishu channel will detect this and send as new message instead of reply
            context["msg"] = None
            logger.debug(f"[Scheduler] Feishu: receive_id_type={context['receive_id_type']}, is_group={is_group}, receiver={receiver}")
        elif channel_type == "dingtalk":
            # DingTalk channel setup
            context["msg"] = None
            # 如果是单聊，需要传递 sender_staff_id
            if not is_group:
                sender_staff_id = action.get("dingtalk_sender_staff_id")
                if sender_staff_id:
                    context["dingtalk_sender_staff_id"] = sender_staff_id
                    logger.debug(f"[Scheduler] DingTalk single chat: sender_staff_id={sender_staff_id}")
                else:
                    logger.warning(f"[Scheduler] Task {task['id']}: DingTalk single chat message missing sender_staff_id")
        elif channel_type == "wecom_bot":
            context["msg"] = None
        elif channel_type == "qq":
            context["msg"] = None

        # Create reply
        reply = Reply(ReplyType.TEXT, content)
        
        # Get channel and send
        try:
            if _send_reply_via_channel(channel_type, reply, context, task):
                logger.info(f"[Scheduler] Task {task['id']} executed: sent message to {receiver}")
            else:
                raise RuntimeError("send message returned false")
        except Exception as e:
            logger.error(f"[Scheduler] Failed to send message: {e}")
            import traceback
            logger.error(f"[Scheduler] Traceback: {traceback.format_exc()}")
            raise
            
    except Exception as e:
        logger.error(f"[Scheduler] Error in _execute_send_message: {e}")
        import traceback
        logger.error(f"[Scheduler] Traceback: {traceback.format_exc()}")
        raise


def _execute_tool_call(task: dict, agent_bridge):
    """
    Execute a tool_call action
    
    Args:
        task: Task dictionary
        agent_bridge: AgentBridge instance
    """
    try:
        action = task.get("action", {})
        # Support both old and new field names
        tool_name = action.get("call_name") or action.get("tool_name")
        tool_params = action.get("call_params") or action.get("tool_params", {})
        result_prefix = action.get("result_prefix", "")
        receiver = action.get("receiver")
        is_group = action.get("is_group", False)
        channel_type = action.get("channel_type", "unknown")
        
        if not tool_name:
            raise RuntimeError("No tool_name specified")
        
        if not receiver:
            raise RuntimeError("No receiver specified")
        
        # Get tool manager and create tool instance
        from agent.tools.tool_manager import ToolManager
        tool_manager = ToolManager()
        tool = tool_manager.create_tool(tool_name)
        
        if not tool:
            raise RuntimeError(f"Tool '{tool_name}' not found")
        
        # Execute tool
        logger.info(f"[Scheduler] Task {task['id']}: Executing tool '{tool_name}' with params {tool_params}")
        result = tool.execute(tool_params)
        
        # Get result content
        if hasattr(result, 'result'):
            content = result.result
        else:
            content = str(result)
        
        # Add prefix if specified
        if result_prefix:
            content = f"{result_prefix}\n\n{content}"
        
        # Send result as message
        context = Context(ContextType.TEXT, content)
        context["receiver"] = receiver
        context["isgroup"] = is_group
        context["session_id"] = receiver
        _apply_task_scope(context, task)
        
        # Channel-specific context setup
        if channel_type == "web":
            # Web channel needs request_id
            import uuid
            request_id = f"scheduler_{task['id']}_{uuid.uuid4().hex[:8]}"
            context["request_id"] = request_id
            logger.debug(f"[Scheduler] Generated request_id for web channel: {request_id}")
        elif channel_type == "feishu":
            context["receive_id_type"] = "chat_id" if is_group else "open_id"
            context["msg"] = None
            logger.debug(f"[Scheduler] Feishu: receive_id_type={context['receive_id_type']}, is_group={is_group}, receiver={receiver}")
        elif channel_type == "wecom_bot":
            context["msg"] = None

        reply = Reply(ReplyType.TEXT, content)

        # Get channel and send
        try:
            if _send_reply_via_channel(channel_type, reply, context, task):
                logger.info(f"[Scheduler] Task {task['id']} executed: sent tool result to {receiver}")
            else:
                raise RuntimeError("send tool result returned false")
        except Exception as e:
            logger.error(f"[Scheduler] Failed to send tool result: {e}")
            raise

    except Exception as e:
        logger.error(f"[Scheduler] Error in _execute_tool_call: {e}")
        raise


def _execute_skill_call(task: dict, agent_bridge):
    """
    Execute a skill_call action by asking Agent to run the skill
    
    Args:
        task: Task dictionary
        agent_bridge: AgentBridge instance
    """
    try:
        action = task.get("action", {})
        # Support both old and new field names
        skill_name = action.get("call_name") or action.get("skill_name")
        skill_params = action.get("call_params") or action.get("skill_params", {})
        result_prefix = action.get("result_prefix", "")
        receiver = action.get("receiver")
        is_group = action.get("isgroup", False)
        channel_type = action.get("channel_type", "unknown")
        
        if not skill_name:
            raise RuntimeError("No skill_name specified")
        
        if not receiver:
            raise RuntimeError("No receiver specified")
        
        logger.info(f"[Scheduler] Task {task['id']}: Executing skill '{skill_name}' with params {skill_params}")
        
        # Create a unique session_id for this scheduled task to avoid polluting user's conversation
        # Format: scheduler_<receiver>_<task_id> to ensure isolation
        scheduler_session_id = f"scheduler_{receiver}_{task['id']}"
        
        # Build a natural language query for the Agent to execute the skill
        # Format: "Use skill-name to do something with params"
        param_str = ", ".join([f"{k}={v}" for k, v in skill_params.items()])
        query = f"Use {skill_name} skill"
        if param_str:
            query += f" with {param_str}"
        
        # Create context for Agent
        context = Context(ContextType.TEXT, query)
        context["receiver"] = receiver
        context["isgroup"] = is_group
        context["session_id"] = scheduler_session_id
        _apply_task_scope(context, task)
        
        # Channel-specific setup
        if channel_type == "web":
            import uuid
            request_id = f"scheduler_{task['id']}_{uuid.uuid4().hex[:8]}"
            context["request_id"] = request_id
        elif channel_type == "feishu":
            context["receive_id_type"] = "chat_id" if is_group else "open_id"
            context["msg"] = None
        elif channel_type == "wecom_bot":
            context["msg"] = None

        # Use Agent to execute the skill
        try:
            # Don't clear history - scheduler tasks use isolated session_id so they won't pollute user conversations
            reply = agent_bridge.agent_reply(query, context=context, on_event=None, clear_history=False)
            
            if reply and reply.content:
                content = reply.content
                
                # Add prefix if specified
                if result_prefix:
                    content = f"{result_prefix}\n\n{content}"
                
                logger.info(f"[Scheduler] Task {task['id']} executed: skill result sent to {receiver}")
            else:
                raise RuntimeError("No result from skill execution")
                
        except Exception as e:
            logger.error(f"[Scheduler] Failed to execute skill via Agent: {e}")
            import traceback
            logger.error(f"[Scheduler] Traceback: {traceback.format_exc()}")
            raise
            
    except Exception as e:
        logger.error(f"[Scheduler] Error in _execute_skill_call: {e}")
        import traceback
        logger.error(f"[Scheduler] Traceback: {traceback.format_exc()}")
        raise


def _task_scope(task: dict) -> dict[str, str]:
    action = task.get("action", {}) if isinstance(task.get("action"), dict) else {}
    return {
        "tenant_id": str(task.get("tenant_id") or action.get("tenant_id") or ""),
        "agent_id": str(task.get("agent_id") or action.get("agent_id") or ""),
        "binding_id": str(task.get("binding_id") or action.get("binding_id") or ""),
        "channel_config_id": str(task.get("channel_config_id") or action.get("channel_config_id") or ""),
        "channel_type": str(action.get("channel_type") or task.get("channel_type") or ""),
    }


def _apply_task_scope(context: Context, task: dict) -> None:
    scope = _task_scope(task)
    for key, value in scope.items():
        if value:
            context[key] = value


def _channel_runtime_overrides(task: dict) -> dict:
    channel_config_id = _task_scope(task).get("channel_config_id", "")
    if not channel_config_id:
        return {}
    try:
        from cow_platform.services.channel_config_service import ChannelConfigService

        service = ChannelConfigService()
        definition = service.resolve_channel_config(channel_config_id=channel_config_id)
        return service.build_runtime_overrides(definition)
    except Exception as e:
        logger.warning(f"[Scheduler] Failed to resolve channel runtime overrides for {channel_config_id}: {e}")
        return {}


def _send_reply_via_channel(channel_type: str, reply: Reply, context: Context, task: dict) -> bool:
    from channel.channel_factory import create_channel
    from cow_platform.runtime.scope import activate_config_overrides

    scope = _task_scope(task)
    channel_config_id = scope.get("channel_config_id", "")
    overrides = _channel_runtime_overrides(task)
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


def attach_scheduler_to_tool(tool, context: Context = None):
    """
    Attach scheduler components to a SchedulerTool instance
    
    Args:
        tool: SchedulerTool instance
        context: Current context (optional)
    """
    if _task_store:
        tool.task_store = _task_store
    
    if context:
        tool.current_context = context
        
        channel_type = context.get("channel_type") or conf().get("channel_type", "unknown")
        if not tool.config:
            tool.config = {}
        tool.config["channel_type"] = channel_type
