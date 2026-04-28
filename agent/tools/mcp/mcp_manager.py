"""
MCP Manager — manages the lifecycle of multiple MCP Server clients.
"""

import asyncio
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

from agent.tools.mcp.mcp_client import MCPClient
from common.log import logger


class MCPManager:
    """Manages multiple MCPClient instances and provides unified tool access."""

    def __init__(self):
        self._clients: dict[str, MCPClient] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._loop_ready = threading.Event()
        self._loop_lock = threading.Lock()

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

    def start_servers_sync(self, mcp_servers: dict, timeout: float = 60.0) -> None:
        """Start long-lived MCP servers on the manager-owned background loop."""
        self._run_on_background_loop(self.start_servers(mcp_servers), timeout=timeout)

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

    def get_all_tools_sync(self, timeout: float = 30.0) -> list[dict]:
        """Collect tools from the same background loop that owns the subprocesses."""
        return self._run_on_background_loop(self.get_all_tools(), timeout=timeout)

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

    def call_tool_sync(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict,
        cancel_event: threading.Event = None,
        timeout: float = 120.0,
    ) -> dict:
        """Call a tool on the manager-owned background loop.

        Long-lived MCP stdio streams are bound to the event loop that created
        the subprocess. Routing every call through the same loop avoids
        ``Future attached to a different loop`` failures.
        """
        return self._run_on_background_loop(
            self.call_tool(
                server_name,
                tool_name,
                arguments,
                cancel_event=cancel_event,
            ),
            timeout=timeout,
        )

    async def shutdown_all(self):
        """Shut down all running MCP servers."""
        for server_name, client in self._clients.items():
            try:
                await client.shutdown()
            except Exception as e:
                logger.error(f"[MCPManager] Error shutting down server '{server_name}': {e}")
        self._clients.clear()
        logger.info("[MCPManager] All MCP servers shut down")

    def shutdown_all_sync(self, timeout: float = 10.0) -> None:
        """Shut down all clients and stop the manager-owned background loop."""
        try:
            self._run_on_background_loop(self.shutdown_all(), timeout=timeout)
        finally:
            self._stop_background_loop(timeout=timeout)

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

    def _ensure_background_loop(self) -> asyncio.AbstractEventLoop:
        with self._loop_lock:
            if self._loop and self._loop.is_running():
                return self._loop

            if not self._loop_thread or not self._loop_thread.is_alive():
                self._loop_ready.clear()
                self._loop_thread = threading.Thread(
                    target=self._run_background_loop,
                    name="cowagent-mcp-loop",
                    daemon=True,
                )
                self._loop_thread.start()

        if not self._loop_ready.wait(timeout=5.0):
            raise RuntimeError("MCP background event loop did not start")
        if self._loop is None:
            raise RuntimeError("MCP background event loop is unavailable")
        return self._loop

    def _run_background_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._loop_ready.set()
        try:
            loop.run_forever()
        finally:
            pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()

    def _run_on_background_loop(self, coroutine: Any, timeout: float | None = None) -> Any:
        loop = self._ensure_background_loop()
        if self._loop_thread is threading.current_thread():
            raise RuntimeError("cannot synchronously wait on the MCP background event loop")
        future = asyncio.run_coroutine_threadsafe(coroutine, loop)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            future.cancel()
            raise TimeoutError(f"MCP operation timed out after {timeout}s")

    def _stop_background_loop(self, timeout: float = 10.0) -> None:
        with self._loop_lock:
            loop = self._loop
            thread = self._loop_thread
            self._loop = None
            self._loop_thread = None
            self._loop_ready.clear()

        if loop and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        if thread and thread is not threading.current_thread():
            thread.join(timeout=timeout)
