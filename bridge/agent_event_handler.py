"""
Agent Event Handler - Handles agent events and thinking process output
"""

from common.log import logger


class AgentEventHandler:
    """
    Handles agent events and optionally sends intermediate messages to channel
    """
    
    def __init__(self, context=None, original_callback=None):
        """
        Initialize event handler
        
        Args:
            context: COW context (for accessing channel)
            original_callback: Original event callback to chain
        """
        self.context = context
        self.original_callback = original_callback
        
        # Get channel for sending intermediate messages
        self.channel = None
        if context:
            self.channel = context.kwargs.get("channel") if hasattr(context, "kwargs") else None
        
        self.current_content = ""
        self.turn_number = 0
        self._usage_metrics = {
            "tool_call_count": 0,
            "mcp_call_count": 0,
            "tool_error_count": 0,
            "tool_execution_time_ms": 0,
            "tool_names": {},
        }
    
    def handle_event(self, event):
        """
        Main event handler
        
        Args:
            event: Event dict with type and data
        """
        event_type = event.get("type")
        data = event.get("data", {})
        
        # Dispatch to specific handlers
        if event_type == "turn_start":
            self._handle_turn_start(data)
        elif event_type == "message_update":
            self._handle_message_update(data)
        elif event_type == "message_end":
            self._handle_message_end(data)
        elif event_type == "reasoning_update":
            pass
        elif event_type == "tool_execution_start":
            self._handle_tool_execution_start(data)
        elif event_type == "tool_execution_end":
            self._handle_tool_execution_end(data)
        
        # Call original callback if provided
        if self.original_callback:
            self.original_callback(event)
    
    def _handle_turn_start(self, data):
        """Handle turn start event"""
        self.turn_number = data.get("turn", 0)
        self.current_content = ""
    
    def _handle_message_update(self, data):
        """Handle message update event (streaming content text)"""
        delta = data.get("delta", "")
        self.current_content += delta
    
    def _handle_message_end(self, data):
        """Handle message end event"""
        tool_calls = data.get("tool_calls", [])
        
        if tool_calls:
            if self.current_content.strip():
                logger.info(f"💭 {self.current_content.strip()[:200]}{'...' if len(self.current_content) > 200 else ''}")
                self._send_to_channel(self.current_content.strip())
        else:
            if self.current_content.strip():
                logger.debug(f"💬 {self.current_content.strip()[:200]}{'...' if len(self.current_content) > 200 else ''}")
        
        self.current_content = ""
    
    def _handle_tool_execution_start(self, data):
        """Handle tool execution start event - logged by agent_stream.py"""
        pass

    def _handle_tool_execution_end(self, data):
        """Handle tool execution end event - logged by agent_stream.py"""
        tool_name = str(data.get("tool_name", "") or "")
        status = str(data.get("status", "") or "")
        execution_time = float(data.get("execution_time", 0) or 0)
        execution_time_ms = max(0, int(round(execution_time * 1000)))

        self._usage_metrics["tool_call_count"] += 1
        self._usage_metrics["tool_execution_time_ms"] += execution_time_ms

        if tool_name:
            tool_names = self._usage_metrics["tool_names"]
            tool_names[tool_name] = int(tool_names.get(tool_name, 0)) + 1

        if tool_name.startswith("mcp_"):
            self._usage_metrics["mcp_call_count"] += 1

        if status and status != "success":
            self._usage_metrics["tool_error_count"] += 1
    
    def _send_to_channel(self, message):
        """
        Try to send intermediate message to channel.
        Skipped in SSE mode because thinking text is already streamed via on_event.
        """
        if self.context and self.context.get("on_event"):
            return

        if self.channel:
            try:
                from bridge.reply import Reply, ReplyType
                reply = Reply(ReplyType.TEXT, message)
                self.channel._send(reply, self.context)
            except Exception as e:
                logger.debug(f"[AgentEventHandler] Failed to send to channel: {e}")
    
    def log_summary(self):
        """Log execution summary - simplified"""
        # Summary removed as per user request
        # Real-time logging during execution is sufficient
        pass

    def get_usage_metrics(self):
        """Return a snapshot of usage metrics collected during the current run."""
        return {
            "tool_call_count": int(self._usage_metrics["tool_call_count"]),
            "mcp_call_count": int(self._usage_metrics["mcp_call_count"]),
            "tool_error_count": int(self._usage_metrics["tool_error_count"]),
            "tool_execution_time_ms": int(self._usage_metrics["tool_execution_time_ms"]),
            "tool_names": dict(self._usage_metrics["tool_names"]),
        }
