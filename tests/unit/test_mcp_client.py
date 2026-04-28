"""
Unit tests for MCP client, manager, and tool — using mock subprocess.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.tools.base_tool import ToolResult
from agent.tools.mcp.mcp_client import MCPClient
from agent.tools.mcp.mcp_manager import MCPManager
from agent.tools.mcp.mcp_tool import MCPTool


# ---------------------------------------------------------------------------
# Helpers — fake subprocess that speaks JSON-RPC over stdin/stdout
# ---------------------------------------------------------------------------

class _FakeStreamReader:
    """Async iterable that returns pre-loaded lines."""

    def __init__(self, lines: list[bytes]):
        self._lines = list(lines)
        self._idx = 0

    def readline(self):
        if self._idx >= len(self._lines):
            # Return empty bytes to simulate EOF
            fut = asyncio.get_event_loop().create_future()
            fut.set_result(b"")
            return fut
        line = self._lines[self._idx]
        self._idx += 1
        fut = asyncio.get_event_loop().create_future()
        fut.set_result(line)
        return fut


class _FakeStreamWriter:
    """Captures written bytes so tests can inspect them."""

    def __init__(self):
        self.written: list[bytes] = []

    def write(self, data: bytes):
        self.written.append(data)

    async def drain(self):
        pass

    def is_closing(self):
        return False

    async def wait_closed(self):
        pass

    def close(self):
        pass


def _make_fake_process(responses: list[dict]):
    """Build a fake asyncio.subprocess.Process that returns *responses* in order."""
    stdout_lines = [(json.dumps(r) + "\n").encode() for r in responses]
    fake_stdout = _FakeStreamReader(stdout_lines)
    fake_stdin = _FakeStreamWriter()

    proc = MagicMock()
    proc.pid = 12345
    proc.stdout = fake_stdout
    proc.stdin = fake_stdin
    proc.stderr = _FakeStreamReader([])
    proc.wait = AsyncMock(return_value=0)
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    return proc, fake_stdin


# ---------------------------------------------------------------------------
# MCPClient tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_client_initialize():
    """Verify the initialize handshake (initialize request + initialized notification)."""
    init_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "serverInfo": {"name": "test-server", "version": "1.0.0"},
        },
    }
    fake_proc, fake_stdin = _make_fake_process([init_response])

    client = MCPClient(server_name="test", command="echo", args=["hello"])
    with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
        await client.start()

    assert client._initialized is True

    # Verify the initialize request was written
    init_request = json.loads(fake_stdin.written[0])
    assert init_request["method"] == "initialize"
    assert init_request["params"]["protocolVersion"] == "2024-11-05"
    assert init_request["params"]["clientInfo"]["name"] == "cowagent"

    # Verify the initialized notification was written
    notification = json.loads(fake_stdin.written[1])
    assert notification["method"] == "notifications/initialized"
    assert "id" not in notification  # notifications have no id

    await client.shutdown()


@pytest.mark.asyncio
async def test_mcp_client_list_tools():
    """Verify tools/list request and response parsing."""
    tools_response = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "tools": [
                {
                    "name": "read_file",
                    "description": "Read a file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
                {
                    "name": "write_file",
                    "description": "Write a file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                        "required": ["path", "content"],
                    },
                },
            ]
        },
    }
    fake_proc, _ = _make_fake_process([tools_response])

    client = MCPClient(server_name="fs", command="npx", args=["-y", "@mcp/server-fs"])
    # Simulate already started (skip handshake)
    client._process = fake_proc
    client._initialized = True
    client._request_id = 1  # start after what handshake would have used

    tools = await client.list_tools()
    assert len(tools) == 2
    assert tools[0]["name"] == "read_file"
    assert tools[1]["name"] == "write_file"

    await client.shutdown()


@pytest.mark.asyncio
async def test_mcp_client_call_tool():
    """Verify tools/call request and result parsing."""
    call_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {"type": "text", "text": "Hello from MCP tool!"},
            ],
        },
    }
    fake_proc, fake_stdin = _make_fake_process([call_response])

    client = MCPClient(server_name="srv", command="echo", args=[])
    client._process = fake_proc
    client._initialized = True

    result = await client.call_tool("greet", {"name": "world"})
    assert result["content"][0]["text"] == "Hello from MCP tool!"

    # Verify the call request
    req = json.loads(fake_stdin.written[0])
    assert req["method"] == "tools/call"
    assert req["params"]["name"] == "greet"
    assert req["params"]["arguments"] == {"name": "world"}

    await client.shutdown()


@pytest.mark.asyncio
async def test_mcp_client_shutdown():
    """Verify graceful shutdown terminates the process."""
    fake_proc, _ = _make_fake_process([])

    client = MCPClient(server_name="shut", command="echo", args=[])
    client._process = fake_proc
    client._initialized = True

    await client.shutdown()

    assert client._process is None
    assert client._initialized is False
    fake_proc.terminate.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_client_not_started_raises():
    """Calling methods before start() should raise RuntimeError."""
    client = MCPClient(server_name="nope", command="echo", args=[])
    with pytest.raises(RuntimeError, match="not started"):
        await client._send_request("tools/list")


# ---------------------------------------------------------------------------
# MCPManager tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_manager_lifecycle():
    """Verify MCPManager starts servers, lists tools, and shuts down."""
    manager = MCPManager()

    # Mock MCPClient so we don't need a real subprocess
    mock_client = MagicMock(spec=MCPClient)
    mock_client.start = AsyncMock()
    mock_client.shutdown = AsyncMock()
    mock_client.list_tools = AsyncMock(return_value=[
        {"name": "tool_a", "description": "Tool A", "inputSchema": {"type": "object", "properties": {}}},
    ])

    with patch("agent.tools.mcp.mcp_manager.MCPClient", return_value=mock_client):
        await manager.start_servers({
            "my_server": {"command": "npx", "args": ["-y", "@mcp/test"], "env": {}}
        })

    assert "my_server" in manager.clients

    # Get all tools
    all_tools = await manager.get_all_tools()
    assert len(all_tools) == 1
    assert all_tools[0]["server_name"] == "my_server"
    assert all_tools[0]["tool_name"] == "tool_a"

    # Call tool
    mock_client.call_tool = AsyncMock(return_value={"content": [{"type": "text", "text": "ok"}]})
    result = await manager.call_tool("my_server", "tool_a", {})
    assert result["content"][0]["text"] == "ok"

    # Shutdown
    await manager.shutdown_all()
    assert len(manager.clients) == 0


@pytest.mark.asyncio
async def test_mcp_manager_call_tool_missing_server():
    """Calling a tool on a non-existent server raises KeyError."""
    manager = MCPManager()
    with pytest.raises(KeyError, match="not_found"):
        await manager.call_tool("not_found", "tool_x", {})


def test_mcp_manager_sync_bridge_keeps_subprocess_on_one_loop():
    """Long-lived sync bridge starts, lists, and calls tools on one background loop."""
    init_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "serverInfo": {"name": "chart", "version": "1.0.0"},
        },
    }
    tools_response = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "tools": [
                {"name": "generate_spreadsheet", "description": "chart", "inputSchema": {}},
            ],
        },
    }
    call_response = {
        "jsonrpc": "2.0",
        "id": 3,
        "result": {"content": [{"type": "text", "text": "chart ok"}]},
    }
    fake_proc, _ = _make_fake_process([init_response, tools_response, call_response])

    manager = MCPManager()
    with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
        manager.start_servers_sync({"chart": {"command": "npx", "args": ["-y", "@antv/mcp-server-chart"]}})
        tools = manager.get_all_tools_sync()
        result = manager.call_tool_sync("chart", "generate_spreadsheet", {"columns": ["排名"]})

    assert tools[0]["tool_name"] == "generate_spreadsheet"
    assert result["content"][0]["text"] == "chart ok"
    manager.shutdown_all_sync()


@pytest.mark.asyncio
async def test_mcp_manager_test_connection_success():
    """test_connection returns success dict when the server works."""
    mock_client = MagicMock(spec=MCPClient)
    mock_client.start = AsyncMock()
    mock_client.shutdown = AsyncMock()
    mock_client.list_tools = AsyncMock(return_value=[
        {"name": "t1", "description": "desc", "inputSchema": {}},
    ])

    manager = MCPManager()
    with patch("agent.tools.mcp.mcp_manager.MCPClient", return_value=mock_client):
        result = await manager.test_connection("npx", ["-y", "@mcp/test"])

    assert result["success"] is True
    assert len(result["tools"]) == 1
    assert result["error"] == ""


@pytest.mark.asyncio
async def test_mcp_manager_test_connection_failure():
    """test_connection returns failure dict when the server fails."""
    mock_client = MagicMock(spec=MCPClient)
    mock_client.start = AsyncMock(side_effect=RuntimeError("spawn failed"))
    mock_client.shutdown = AsyncMock()

    manager = MCPManager()
    with patch("agent.tools.mcp.mcp_manager.MCPClient", return_value=mock_client):
        result = await manager.test_connection("bad-cmd", [])

    assert result["success"] is False
    assert "spawn failed" in result["error"]


# ---------------------------------------------------------------------------
# MCPTool tests
# ---------------------------------------------------------------------------

def test_mcp_tool_registration():
    """Verify MCPTool correctly wraps MCP tool metadata as a BaseTool."""
    manager = MCPManager()

    tool = MCPTool(
        server_name="fs",
        tool_name="read_file",
        description="Read a file from filesystem",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
            },
            "required": ["path"],
        },
        mcp_manager=manager,
    )

    assert tool.name == "mcp_fs_read_file"
    assert tool.description == "Read a file from filesystem"
    assert tool.params["type"] == "object"
    assert "path" in tool.params["properties"]

    # Verify get_json_schema
    schema = tool.get_json_schema()
    assert schema["name"] == "mcp_fs_read_file"
    assert schema["parameters"] == tool.params


def test_mcp_tool_execute_success():
    """Verify MCPTool.execute returns a success ToolResult."""
    manager = MCPManager()

    # Mock the sync bridge that keeps long-lived MCP subprocesses on one loop.
    with patch.object(manager, "call_tool_sync") as mock_call:
        mock_call.return_value = {
            "content": [{"type": "text", "text": "file contents here"}],
        }

        tool = MCPTool(
            server_name="fs",
            tool_name="read_file",
            description="Read file",
            input_schema={"type": "object", "properties": {}},
            mcp_manager=manager,
        )

        result = tool.execute({"path": "/tmp/test.txt"})
        assert isinstance(result, ToolResult)
        assert result.status == "success"
        assert result.result == "file contents here"


def test_mcp_tool_execute_error():
    """Verify MCPTool.execute returns a fail ToolResult on exception."""
    manager = MCPManager()

    with patch.object(manager, "call_tool_sync") as mock_call:
        mock_call.side_effect = RuntimeError("connection lost")

        tool = MCPTool(
            server_name="fs",
            tool_name="read_file",
            description="Read file",
            input_schema={"type": "object", "properties": {}},
            mcp_manager=manager,
        )

        result = tool.execute({"path": "/tmp/test.txt"})
        assert isinstance(result, ToolResult)
        assert result.status == "error"
        assert "connection lost" in result.result


def test_mcp_tool_uses_manager_background_loop_bridge():
    """MCPTool routes calls through MCPManager.call_tool_sync."""
    manager = MCPManager()
    with patch.object(manager, "call_tool_sync", return_value={"content": [{"type": "text", "text": "ok"}]}) as mock_call:
        tool = MCPTool(
            server_name="chart",
            tool_name="generate_spreadsheet",
            description="Generate a spreadsheet chart",
            input_schema={"type": "object", "properties": {}},
            mcp_manager=manager,
        )

        result = tool.execute({"columns": ["排名"], "data": []})

    assert result.status == "success"
    assert result.result == "ok"
    mock_call.assert_called_once()
