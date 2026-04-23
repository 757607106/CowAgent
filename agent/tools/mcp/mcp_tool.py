"""
MCPTool — wraps a single MCP tool as a BaseTool so the Agent can use it.
"""

import asyncio
import json

from agent.tools.base_tool import BaseTool, ToolResult
from agent.tools.mcp.mcp_manager import MCPManager
from common.log import logger


class MCPTool(BaseTool):
    """Wraps a single MCP tool as an Agent-usable BaseTool.

    The tool name follows the pattern: ``mcp_{server_name}_{tool_name}``
    """

    # Class-level placeholders (overridden per instance)
    name: str = "mcp_tool"
    description: str = "MCP tool"
    params: dict = {}

    def __init__(
        self,
        server_name: str,
        tool_name: str,
        description: str,
        input_schema: dict,
        mcp_manager: MCPManager,
    ):
        self.server_name = server_name
        self.tool_name = tool_name
        self.mcp_manager = mcp_manager

        # Build the composite name
        self.name = f"mcp_{server_name}_{tool_name}"
        self.description = description or f"MCP tool: {server_name}/{tool_name}"

        # Convert MCP inputSchema → BaseTool params (JSON Schema format)
        self.params = input_schema if input_schema else {
            "type": "object",
            "properties": {},
        }

    def execute(self, params: dict) -> ToolResult:
        """Synchronous entry point required by BaseTool.

        Bridges to the async MCPManager.call_tool using the current event loop
        (or creates one if none is running).
        """
        try:
            arguments = dict(params) if params else {}
            # Extract cancel_token from context if available
            cancel_token = None
            if hasattr(self, 'context') and self.context is not None:
                # context is the Agent instance; check for cancel_token
                cancel_token = getattr(self.context, '_current_cancel_token', None)
            result = self._run_async(arguments, cancel_token=cancel_token)
            # Serialize the result to a string for the agent
            if isinstance(result, dict):
                # MCP tool results have a "content" list
                content = result.get("content", [])
                if content:
                    text_parts = [
                        c.get("text", "")
                        for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                    ]
                    if text_parts:
                        return ToolResult.success("\n".join(text_parts))
                # Fallback: return raw JSON
                return ToolResult.success(json.dumps(result, ensure_ascii=False))
            return ToolResult.success(str(result))
        except Exception as e:
            logger.error(f"[MCPTool] Error executing {self.name}: {e}")
            return ToolResult.fail(str(e))

    def _run_async(self, arguments: dict, cancel_token=None) -> dict:
        """Run an async call_tool in a compatible way with the current loop."""
        # Convert CancelToken to threading.Event for MCPClient compatibility
        cancel_event = None
        if cancel_token is not None:
            cancel_event = cancel_token._event

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're inside an async context (e.g. the agent loop itself);
            # schedule the coroutine and block until it completes.
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, self.mcp_manager.call_tool(
                    self.server_name, self.tool_name, arguments,
                    cancel_event=cancel_event
                ))
                return future.result(timeout=120)
        else:
            # No running loop — safe to use asyncio.run
            return asyncio.run(
                self.mcp_manager.call_tool(
                    self.server_name, self.tool_name, arguments,
                    cancel_event=cancel_event
                )
            )

    def get_json_schema(self) -> dict:
        """Return JSON Schema for tool registration (instance method)."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.params,
        }
