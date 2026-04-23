"""
MCP stdio protocol client — communicates with MCP Server via subprocess stdin/stdout
using JSON-RPC 2.0 (newline-delimited).
"""

import asyncio
import json
import os
import threading
from typing import Any, Optional

from common.log import logger


class MCPClient:
    """Client for communicating with an MCP Server over stdio (subprocess)."""

    def __init__(self, server_name: str, command: str, args: list, env: dict = None):
        """Initialize but do not start the subprocess.

        Args:
            server_name: Logical name for this server (used in tool naming).
            command: Executable command to launch the server (e.g. "npx").
            args: Arguments passed to the command.
            env: Optional extra environment variables merged into os.environ.
        """
        self.server_name = server_name
        self.command = command
        self.args = list(args)
        self.env = env or {}

        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self):
        """Launch the server subprocess, perform MCP initialize handshake."""
        merged_env = dict(os.environ)
        merged_env.update(self.env)

        self._process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=merged_env,
        )
        logger.info(f"[MCPClient] Started server '{self.server_name}' (pid={self._process.pid})")

        # 1) Send initialize request
        init_result = await self._send_request(
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "cowagent", "version": "2.0.6"},
            },
        )
        if "error" in init_result:
            raise RuntimeError(
                f"MCP initialize failed for '{self.server_name}': {init_result['error']}"
            )

        # 2) Send initialized notification
        await self._send_notification(method="notifications/initialized")

        self._initialized = True
        logger.info(f"[MCPClient] Server '{self.server_name}' initialized successfully")

    async def shutdown(self):
        """Gracefully shut down the server subprocess."""
        if self._process is None:
            return
        try:
            if self._process.stdin and not self._process.stdin.is_closing():
                self._process.stdin.close()
                await self._process.stdin.wait_closed()
        except Exception:
            pass
        try:
            self._process.terminate()
            await asyncio.wait_for(self._process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            self._process.kill()
            await self._process.wait()
        except Exception:
            pass
        self._process = None
        self._initialized = False
        logger.info(f"[MCPClient] Server '{self.server_name}' shut down")

    # ------------------------------------------------------------------
    # MCP operations
    # ------------------------------------------------------------------

    async def list_tools(self) -> list[dict]:
        """Return the list of tools exposed by this server."""
        result = await self._send_request(method="tools/list")
        if "error" in result:
            raise RuntimeError(f"tools/list failed: {result['error']}")
        return result.get("result", {}).get("tools", [])

    async def call_tool(self, tool_name: str, arguments: dict,
                       cancel_event: threading.Event = None,
                       timeout: float = 120.0) -> dict:
        """Call a specific tool on this server.

        Args:
            tool_name: Name of the tool (as reported by list_tools).
            arguments: Keyword arguments for the tool.
            cancel_event: Optional threading.Event — if set, abort the call.
            timeout: Maximum seconds to wait for a response (default: 120).

        Returns:
            The tool result payload.

        Raises:
            RuntimeError: If the call fails or is cancelled.
        """
        try:
            result = await asyncio.wait_for(
                self._send_request(
                    method="tools/call",
                    params={"name": tool_name, "arguments": arguments},
                    cancel_event=cancel_event,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"tools/call '{tool_name}' timed out after {timeout}s"
            )
        if "error" in result:
            raise RuntimeError(f"tools/call '{tool_name}' failed: {result['error']}")
        return result.get("result", {})

    # ------------------------------------------------------------------
    # JSON-RPC transport
    # ------------------------------------------------------------------

    async def _send_request(self, method: str, params: dict = None,
                            cancel_event: threading.Event = None) -> dict:
        """Send a JSON-RPC 2.0 request and wait for the response.

        Args:
            method: RPC method name.
            params: Optional parameters.
            cancel_event: If provided and set, abort waiting for the response.
        """
        if self._process is None or self._process.stdin is None:
            raise RuntimeError(f"MCPClient for '{self.server_name}' is not started")

        self._request_id += 1
        request: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params is not None:
            request["params"] = params

        line = json.dumps(request) + "\n"
        self._process.stdin.write(line.encode("utf-8"))
        await self._process.stdin.drain()

        # Read one response line, with optional cancellation check
        while True:
            try:
                response_line = await asyncio.wait_for(
                    self._process.stdout.readline(), timeout=1.0
                )
                if not response_line:
                    raise RuntimeError(
                        f"MCP server '{self.server_name}' closed stdout unexpectedly"
                    )
                break
            except asyncio.TimeoutError:
                # Check cancellation
                if cancel_event is not None and cancel_event.is_set():
                    raise RuntimeError(
                        f"MCP call to '{self.server_name}' cancelled"
                    )
                # Otherwise, just keep waiting
                continue

        response = json.loads(response_line.decode("utf-8").strip())

        # Match response id to request id
        if response.get("id") != self._request_id:
            logger.warning(
                f"[MCPClient] Response id mismatch: expected {self._request_id}, "
                f"got {response.get('id')}"
            )
        return response

    async def _send_notification(self, method: str, params: dict = None):
        """Send a JSON-RPC 2.0 notification (no id, no response expected)."""
        if self._process is None or self._process.stdin is None:
            raise RuntimeError(f"MCPClient for '{self.server_name}' is not started")

        notification: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            notification["params"] = params

        line = json.dumps(notification) + "\n"
        self._process.stdin.write(line.encode("utf-8"))
        await self._process.stdin.drain()
