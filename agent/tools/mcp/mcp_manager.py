"""
MCP Manager — manages the lifecycle of multiple MCP Server clients.
"""

import asyncio
import threading

from agent.tools.mcp.mcp_client import MCPClient
from common.log import logger


class MCPManager:
    """Manages multiple MCPClient instances and provides unified tool access."""

    def __init__(self):
        self._clients: dict[str, MCPClient] = {}

    @property
    def clients(self) -> dict[str, MCPClient]:
        return self._clients

    async def start_servers(self, mcp_servers: dict):
        """Start all MCP servers from the configuration dict.

        Args:
            mcp_servers: Mapping of server_name → {command, args, env?}.
        """
        for server_name, config in mcp_servers.items():
            command = config.get("command", "")
            args = config.get("args", [])
            env = config.get("env", None)
            if not command:
                logger.warning(f"[MCPManager] Skipping server '{server_name}': no command specified")
                continue
            try:
                client = MCPClient(
                    server_name=server_name,
                    command=command,
                    args=args,
                    env=env,
                )
                await client.start()
                self._clients[server_name] = client
                logger.info(f"[MCPManager] Started server '{server_name}'")
            except Exception as e:
                logger.error(f"[MCPManager] Failed to start server '{server_name}': {e}")

    async def get_all_tools(self) -> list[dict]:
        """Collect tools from all running servers.

        Returns:
            List of dicts with keys: server_name, tool_name, description, input_schema.
        """
        all_tools: list[dict] = []
        for server_name, client in self._clients.items():
            try:
                tools = await client.list_tools()
                for tool in tools:
                    all_tools.append({
                        "server_name": server_name,
                        "tool_name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                        "input_schema": tool.get("inputSchema", {}),
                    })
            except Exception as e:
                logger.error(f"[MCPManager] Failed to list tools for '{server_name}': {e}")
        return all_tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict,
                       cancel_event: threading.Event = None) -> dict:
        """Call a tool on a specific server.

        Args:
            server_name: The server that owns the tool.
            tool_name: The tool name within that server.
            arguments: Tool arguments.
            cancel_event: Optional threading.Event for cancellation support.

        Returns:
            The tool result payload.

        Raises:
            KeyError: If the server is not found.
        """
        client = self._clients.get(server_name)
        if client is None:
            raise KeyError(f"MCP server '{server_name}' not found")
        return await client.call_tool(tool_name, arguments, cancel_event=cancel_event)

    async def shutdown_all(self):
        """Shut down all running MCP servers."""
        for server_name, client in self._clients.items():
            try:
                await client.shutdown()
            except Exception as e:
                logger.error(f"[MCPManager] Error shutting down server '{server_name}': {e}")
        self._clients.clear()
        logger.info("[MCPManager] All MCP servers shut down")

    async def test_connection(self, command: str, args: list, env: dict = None) -> dict:
        """Test connectivity to an MCP server without persisting it.

        Args:
            command: Executable to launch.
            args: Command arguments.
            env: Optional extra env vars.

        Returns:
            {"success": bool, "tools": [...], "error": "..."}
        """
        client = MCPClient(
            server_name="__test__",
            command=command,
            args=args,
            env=env,
        )
        try:
            await client.start()
            tools = await client.list_tools()
            tool_list = [
                {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "inputSchema": t.get("inputSchema", {}),
                }
                for t in tools
            ]
            await client.shutdown()
            return {"success": True, "tools": tool_list, "error": ""}
        except Exception as e:
            try:
                await client.shutdown()
            except Exception:
                pass
            return {"success": False, "tools": [], "error": str(e)}
