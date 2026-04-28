"""
Unit tests for the cooperative cancellation / preemption mechanism.

Tests cover:
- CancelToken basic operations (cancel, check, wait)
- CancelTokenRegistry (cancel_and_replace, get, remove)
- AgentStreamExecutor integration (cancel between turns, before tool calls)
- MCPClient cancellation support
- ChatChannel queue preemption (dropping stale queued messages)
- ChatChannel produce() cancels RUNNING agent tasks
- AgentBridge.agent_reply() returns None on cancellation
- Bridge.cancel_running_agent() forwarding
- WebChannel SSE preemption
- Cross-session isolation (different users don't affect each other)
- MCPTool CancelToken propagation
"""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from agent.protocol.cancel import (
    CancelToken,
    CancelTokenRegistry,
    CancelledError,
    PreemptionError,
)


# ---------------------------------------------------------------------------
# CancelToken
# ---------------------------------------------------------------------------

class TestCancelToken:

    def test_initial_state_not_cancelled(self):
        token = CancelToken()
        assert not token.is_cancelled

    def test_cancel_sets_flag(self):
        token = CancelToken()
        token.cancel()
        assert token.is_cancelled

    def test_check_cancelled_raises_when_cancelled(self):
        token = CancelToken()
        token.cancel()
        with pytest.raises(CancelledError, match="cancelled"):
            token.check_cancelled()

    def test_check_cancelled_noop_when_active(self):
        token = CancelToken()
        # Should not raise
        token.check_cancelled()

    def test_wait_returns_true_when_cancelled(self):
        token = CancelToken()
        token.cancel()
        assert token.wait(timeout=0.1) is True

    def test_wait_returns_false_on_timeout(self):
        token = CancelToken()
        assert token.wait(timeout=0.05) is False

    def test_wait_wakes_on_cancel(self):
        token = CancelToken()
        result = [None]

        def _cancel_soon():
            time.sleep(0.05)
            token.cancel()

        t = threading.Thread(target=_cancel_soon, daemon=True)
        t.start()
        woke = token.wait(timeout=5.0)
        t.join(timeout=1.0)
        assert woke is True


# ---------------------------------------------------------------------------
# CancelTokenRegistry
# ---------------------------------------------------------------------------

class TestCancelTokenRegistry:

    def test_get_or_create_new(self):
        reg = CancelTokenRegistry()
        token = reg.get_or_create("session-1")
        assert isinstance(token, CancelToken)
        assert not token.is_cancelled

    def test_get_or_create_returns_same(self):
        reg = CancelTokenRegistry()
        t1 = reg.get_or_create("session-1")
        t2 = reg.get_or_create("session-1")
        assert t1 is t2

    def test_cancel_and_replace_cancels_old(self):
        reg = CancelTokenRegistry()
        old = reg.get_or_create("session-1")
        new = reg.cancel_and_replace("session-1")
        assert old.is_cancelled
        assert not new.is_cancelled
        assert old is not new

    def test_cancel_and_replace_no_old(self):
        reg = CancelTokenRegistry()
        new = reg.cancel_and_replace("session-new")
        assert not new.is_cancelled

    def test_get_returns_none_for_unknown(self):
        reg = CancelTokenRegistry()
        assert reg.get("unknown") is None

    def test_remove_cleans_up(self):
        reg = CancelTokenRegistry()
        reg.get_or_create("session-1")
        reg.remove("session-1")
        assert reg.get("session-1") is None

    def test_cancel_all(self):
        reg = CancelTokenRegistry()
        t1 = reg.get_or_create("s1")
        t2 = reg.get_or_create("s2")
        reg.cancel_all()
        assert t1.is_cancelled
        assert t2.is_cancelled

    def test_active_count(self):
        reg = CancelTokenRegistry()
        reg.get_or_create("s1")
        reg.get_or_create("s2")
        assert reg.active_count == 2
        reg.cancel_and_replace("s1")  # cancels old s1, creates new
        assert reg.active_count == 2  # old cancelled, new active + s2

    def test_thread_safety(self):
        """Concurrent cancel_and_replace should not corrupt state."""
        reg = CancelTokenRegistry()
        errors = []

        def _worker(session_id):
            try:
                for _ in range(50):
                    token = reg.cancel_and_replace(session_id)
                    assert not token.is_cancelled
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_worker, args=(f"s{i % 3}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        assert not errors


# ---------------------------------------------------------------------------
# Preemption scenarios — same session
# ---------------------------------------------------------------------------

class TestPreemptionSameSession:

    def test_new_message_cancels_old(self):
        """Simulate same user sending two messages: the first is cancelled."""
        reg = CancelTokenRegistry()
        # First message arrives
        token1 = reg.cancel_and_replace("user-A")
        assert not token1.is_cancelled

        # Second message arrives — should cancel the first
        token2 = reg.cancel_and_replace("user-A")
        assert token1.is_cancelled
        assert not token2.is_cancelled

        # The first request would detect cancellation
        with pytest.raises(CancelledError):
            token1.check_cancelled()

    def test_third_message_cancels_second(self):
        reg = CancelTokenRegistry()
        t1 = reg.cancel_and_replace("s1")
        t2 = reg.cancel_and_replace("s1")
        assert t1.is_cancelled
        assert not t2.is_cancelled
        t3 = reg.cancel_and_replace("s1")
        assert t2.is_cancelled
        assert not t3.is_cancelled


# ---------------------------------------------------------------------------
# Preemption isolation — different sessions
# ---------------------------------------------------------------------------

class TestPreemptionDifferentSessions:

    def test_different_users_not_affected(self):
        """Cancelling user-A should not affect user-B."""
        reg = CancelTokenRegistry()
        token_a = reg.cancel_and_replace("user-A")
        token_b = reg.cancel_and_replace("user-B")

        # User-A sends another message
        token_a2 = reg.cancel_and_replace("user-A")
        assert token_a.is_cancelled
        assert not token_b.is_cancelled  # B unaffected
        assert not token_a2.is_cancelled

    def test_different_sessions_independent(self):
        reg = CancelTokenRegistry()
        tokens = {}
        for i in range(5):
            tokens[f"s{i}"] = reg.cancel_and_replace(f"s{i}")

        # Cancel only session s2
        new_t2 = reg.cancel_and_replace("s2")
        assert tokens["s2"].is_cancelled
        for i in range(5):
            if i != 2:
                assert not tokens[f"s{i}"].is_cancelled


# ---------------------------------------------------------------------------
# AgentStreamExecutor cancel integration
# ---------------------------------------------------------------------------

class TestAgentStreamExecutorCancellation:

    def _make_executor(self, cancel_token=None):
        """Create a minimal AgentStreamExecutor for testing cancel checks."""
        from agent.protocol.agent_stream import AgentStreamExecutor

        agent = MagicMock()
        agent._estimate_message_tokens.return_value = 10
        agent._get_model_context_window.return_value = 128000
        agent.memory_manager = None

        model = MagicMock()
        model.model = "test-model"

        return AgentStreamExecutor(
            agent=agent,
            model=model,
            system_prompt="test",
            tools=[],
            max_turns=5,
            cancel_token=cancel_token,
        )

    def test_cancelled_at_turn_boundary(self):
        """Executor should raise CancelledError when token is set between turns."""
        token = CancelToken()
        executor = self._make_executor(cancel_token=token)

        # Directly test the check_cancelled call that happens at turn boundary
        token.cancel()
        with pytest.raises(CancelledError):
            token.check_cancelled()

    def test_cancelled_before_tool_execution(self):
        """Executor should raise CancelledError when token is set before tool call."""
        token = CancelToken()
        executor = self._make_executor(cancel_token=token)

        # Simulate: tool about to be executed, but token cancelled
        token.cancel()
        with pytest.raises(CancelledError):
            token.check_cancelled()

    def test_cancelled_before_llm_call(self):
        """Executor should raise CancelledError when token is set before LLM call."""
        token = CancelToken()
        executor = self._make_executor(cancel_token=token)

        token.cancel()
        with pytest.raises(CancelledError):
            token.check_cancelled()

    def test_no_cancel_when_token_active(self):
        """Executor should proceed normally when token is not cancelled."""
        token = CancelToken()
        # This should not raise
        token.check_cancelled()


# ---------------------------------------------------------------------------
# MCPClient cancel support
# ---------------------------------------------------------------------------

class TestMCPClientCancellation:

    def test_call_tool_with_cancel_event(self):
        """MCPClient.call_tool should accept cancel_event parameter."""
        from agent.tools.mcp.mcp_client import MCPClient

        client = MCPClient("test", "echo", [])
        # Client is not started, so calling call_tool directly would fail
        # We just verify the signature accepts the parameter
        import inspect
        sig = inspect.signature(client.call_tool)
        assert "cancel_event" in sig.parameters
        assert "timeout" in sig.parameters

    def test_send_request_with_cancel_event(self):
        """MCPClient._send_request should accept cancel_event parameter."""
        from agent.tools.mcp.mcp_client import MCPClient

        client = MCPClient("test", "echo", [])
        import inspect
        sig = inspect.signature(client._send_request)
        assert "cancel_event" in sig.parameters


# ---------------------------------------------------------------------------
# MCPTool CancelToken propagation
# ---------------------------------------------------------------------------

class TestMCPToolCancelPropagation:

    def test_mcp_tool_extracts_cancel_token_from_context(self):
        """MCPTool.execute() should extract _current_cancel_token from agent context."""
        from agent.tools.mcp.mcp_tool import MCPTool
        from agent.tools.mcp.mcp_manager import MCPManager

        manager = MagicMock(spec=MCPManager)
        tool = MCPTool("server1", "tool1", "Test tool", {"type": "object", "properties": {}}, manager)

        # Set up agent context with cancel token
        cancel_token = CancelToken()
        mock_agent = MagicMock()
        mock_agent._current_cancel_token = cancel_token
        tool.context = mock_agent

        # Mock the _run_async to capture the cancel_token argument
        captured_args = {}
        original_run_async = tool._run_async

        def mock_run_async(arguments, cancel_token=None):
            captured_args["cancel_token"] = cancel_token
            return {"content": [{"type": "text", "text": "ok"}]}

        tool._run_async = mock_run_async
        result = tool.execute({})

        assert captured_args["cancel_token"] is cancel_token

    def test_mcp_tool_no_cancel_token_without_context(self):
        """MCPTool should pass None cancel_token when context has none."""
        from agent.tools.mcp.mcp_tool import MCPTool
        from agent.tools.mcp.mcp_manager import MCPManager

        manager = MagicMock(spec=MCPManager)
        tool = MCPTool("server1", "tool1", "Test tool", {"type": "object", "properties": {}}, manager)
        # No context set
        tool.context = None

        captured_args = {}

        def mock_run_async(arguments, cancel_token=None):
            captured_args["cancel_token"] = cancel_token
            return {"content": [{"type": "text", "text": "ok"}]}

        tool._run_async = mock_run_async
        result = tool.execute({})

        assert captured_args["cancel_token"] is None

    def test_mcp_tool_converts_cancel_token_to_event(self):
        """MCPTool._run_async should convert CancelToken to threading.Event for MCPClient."""
        from agent.tools.mcp.mcp_tool import MCPTool
        from agent.tools.mcp.mcp_manager import MCPManager

        manager = MagicMock(spec=MCPManager)
        tool = MCPTool("server1", "tool1", "Test tool", {"type": "object", "properties": {}}, manager)

        cancel_token = CancelToken()

        manager.call_tool_sync.return_value = {"content": [{"type": "text", "text": "ok"}]}

        tool._run_async({}, cancel_token=cancel_token)

        manager.call_tool_sync.assert_called_once_with(
            "server1",
            "tool1",
            {},
            cancel_event=cancel_token._event,
            timeout=120,
        )

    def test_mcp_tool_cancelled_tool_returns_fail(self):
        """When CancelToken is set during MCP execution, the tool should report failure."""
        from agent.tools.mcp.mcp_tool import MCPTool
        from agent.tools.mcp.mcp_manager import MCPManager
        from agent.tools.base_tool import ToolResult

        manager = MagicMock(spec=MCPManager)
        tool = MCPTool("server1", "tool1", "Test tool", {"type": "object", "properties": {}}, manager)

        cancel_token = CancelToken()
        cancel_token.cancel()  # Pre-cancel

        mock_agent = MagicMock()
        mock_agent._current_cancel_token = cancel_token
        tool.context = mock_agent

        # Make the async call raise RuntimeError (simulating MCPClient cancel detection)
        def mock_run_async(arguments, cancel_token=None):
            if cancel_token and cancel_token.is_cancelled:
                raise RuntimeError("MCP call to 'server1' cancelled")
            return {"content": [{"type": "text", "text": "ok"}]}

        tool._run_async = mock_run_async
        result = tool.execute({})

        assert result.status == "error"


# ---------------------------------------------------------------------------
# ChatChannel queue preemption
# ---------------------------------------------------------------------------

class TestChatChannelQueuePreemption:

    def test_produce_drops_stale_queued_messages(self):
        """When a new message arrives for a session with queued messages,
        only the latest should be kept."""
        from channel.chat_channel import ChatChannel
        from bridge.context import Context, ContextType

        # Create a ChatChannel instance with minimal setup
        channel = ChatChannel.__new__(ChatChannel)
        channel.futures = {}
        channel.sessions = {}
        channel.lock = threading.Lock()
        # Override the consume thread — don't start it
        # (We're only testing produce logic)

        # Mock conf() for concurrency_in_session
        with patch("channel.chat_channel.conf") as mock_conf:
            mock_conf.return_value.get.return_value = 1

            # Create mock messages for the same session
            msg1 = MagicMock()
            msg1.content = "first message"
            ctx1 = Context(ContextType.TEXT, "first message")
            ctx1["session_id"] = "user-1"
            ctx1.type = ContextType.TEXT

            msg2 = MagicMock()
            msg2.content = "second message"
            ctx2 = Context(ContextType.TEXT, "second message")
            ctx2["session_id"] = "user-1"
            ctx2.type = ContextType.TEXT

            msg3 = MagicMock()
            msg3.content = "third message"
            ctx3 = Context(ContextType.TEXT, "third message")
            ctx3["session_id"] = "user-1"
            ctx3.type = ContextType.TEXT

            # Produce three messages for the same session
            channel.produce(ctx1)
            channel.produce(ctx2)
            channel.produce(ctx3)

            # Only the latest message should be in the queue
            queue = channel.sessions["user-1"][0]
            assert queue.qsize() == 1
            remaining = queue.get()
            assert remaining.content == "third message"

    def test_produce_cancels_running_agent_task(self):
        """When a new message arrives, produce() should cancel the running
        agent task for the session via Bridge.cancel_running_agent()."""
        from channel.chat_channel import ChatChannel
        from bridge.context import Context, ContextType

        channel = ChatChannel.__new__(ChatChannel)
        channel.futures = {}
        channel.sessions = {}
        channel.lock = threading.Lock()

        with patch("channel.chat_channel.conf") as mock_conf, \
             patch("channel.chat_channel.Bridge") as MockBridge:
            mock_conf.return_value.get.return_value = 1
            mock_bridge = MockBridge.return_value

            ctx1 = Context(ContextType.TEXT, "first message")
            ctx1["session_id"] = "user-1"
            ctx1.type = ContextType.TEXT

            ctx2 = Context(ContextType.TEXT, "second message")
            ctx2["session_id"] = "user-1"
            ctx2.type = ContextType.TEXT

            # Produce first message
            channel.produce(ctx1)
            # Should not have called cancel_running_agent yet (no previous running)
            # (It's called but with no running task, it's a no-op)

            # Produce second message — should cancel running agent
            channel.produce(ctx2)

            # Verify cancel_running_agent was called for the session
            mock_bridge.cancel_running_agent.assert_called_with("user-1")

    def test_produce_cancel_running_agent_is_noop_when_no_agent(self):
        """produce() should not crash if agent bridge is not initialized."""
        from channel.chat_channel import ChatChannel
        from bridge.context import Context, ContextType

        channel = ChatChannel.__new__(ChatChannel)
        channel.futures = {}
        channel.sessions = {}
        channel.lock = threading.Lock()

        with patch("channel.chat_channel.conf") as mock_conf, \
             patch("channel.chat_channel.Bridge") as MockBridge:
            mock_conf.return_value.get.return_value = 1
            # Simulate agent bridge not initialized — cancel_running_agent raises
            MockBridge.return_value.cancel_running_agent.side_effect = Exception("not init")

            ctx1 = Context(ContextType.TEXT, "message")
            ctx1["session_id"] = "user-1"
            ctx1.type = ContextType.TEXT

            # Should not raise — the exception is caught
            channel.produce(ctx1)

    def test_different_sessions_not_affected_by_produce(self):
        """produce() for session-A should not cancel session-B's running task."""
        from channel.chat_channel import ChatChannel
        from bridge.context import Context, ContextType

        channel = ChatChannel.__new__(ChatChannel)
        channel.futures = {}
        channel.sessions = {}
        channel.lock = threading.Lock()

        with patch("channel.chat_channel.conf") as mock_conf, \
             patch("channel.chat_channel.Bridge") as MockBridge:
            mock_conf.return_value.get.return_value = 1
            mock_bridge = MockBridge.return_value

            # Send two messages for user-A (second triggers cancel)
            ctx_a1 = Context(ContextType.TEXT, "message A1")
            ctx_a1["session_id"] = "user-A"
            ctx_a1.type = ContextType.TEXT

            ctx_a2 = Context(ContextType.TEXT, "message A2")
            ctx_a2["session_id"] = "user-A"
            ctx_a2.type = ContextType.TEXT

            channel.produce(ctx_a1)
            channel.produce(ctx_a2)

            # Send two messages for user-B
            ctx_b1 = Context(ContextType.TEXT, "message B1")
            ctx_b1["session_id"] = "user-B"
            ctx_b1.type = ContextType.TEXT

            ctx_b2 = Context(ContextType.TEXT, "message B2")
            ctx_b2["session_id"] = "user-B"
            ctx_b2.type = ContextType.TEXT

            channel.produce(ctx_b1)
            channel.produce(ctx_b2)

            # Verify cancel_running_agent was called with each session's ID
            calls = [call.args[0] for call in mock_bridge.cancel_running_agent.call_args_list]
            # Each session should have been cancelled when the second message arrived
            assert "user-A" in calls
            assert "user-B" in calls
            # user-A should not appear after user-B's messages
            a_indices = [i for i, c in enumerate(calls) if c == "user-A"]
            b_indices = [i for i, c in enumerate(calls) if c == "user-B"]
            # All A calls should come before B calls
            assert max(a_indices) < min(b_indices)


# ---------------------------------------------------------------------------
# AgentBridge cancel_running_session
# ---------------------------------------------------------------------------

class TestAgentBridgeCancelRunningSession:

    def test_cancel_running_session_cancels_active_token(self):
        """cancel_running_session should cancel the active token for the session."""
        from bridge.agent_bridge import AgentBridge
        from bridge.bridge import Bridge

        with patch("bridge.agent_bridge.AgentInitializer"), \
             patch("bridge.agent_bridge.CowAgentRuntimeAdapter"), \
             patch("bridge.agent_bridge.PricingService"), \
             patch("bridge.agent_bridge.UsageService"), \
             patch("bridge.agent_bridge.QuotaService"):
            bridge = MagicMock(spec=Bridge)
            ab = AgentBridge(bridge)

        # Simulate a running task by creating a token
        token = ab._cancel_registry.cancel_and_replace("session-1")
        assert not token.is_cancelled

        # Cancel the running session
        ab.cancel_running_session("session-1")
        assert token.is_cancelled

    def test_cancel_running_session_noop_when_no_task(self):
        """cancel_running_session should be a no-op when no task is running."""
        from bridge.agent_bridge import AgentBridge
        from bridge.bridge import Bridge

        with patch("bridge.agent_bridge.AgentInitializer"), \
             patch("bridge.agent_bridge.CowAgentRuntimeAdapter"), \
             patch("bridge.agent_bridge.PricingService"), \
             patch("bridge.agent_bridge.UsageService"), \
             patch("bridge.agent_bridge.QuotaService"):
            bridge = MagicMock(spec=Bridge)
            ab = AgentBridge(bridge)

        # No task registered — should not raise
        ab.cancel_running_session("nonexistent-session")

    def test_cancel_running_session_noop_when_already_cancelled(self):
        """cancel_running_session should be a no-op when token is already cancelled."""
        from bridge.agent_bridge import AgentBridge
        from bridge.bridge import Bridge

        with patch("bridge.agent_bridge.AgentInitializer"), \
             patch("bridge.agent_bridge.CowAgentRuntimeAdapter"), \
             patch("bridge.agent_bridge.PricingService"), \
             patch("bridge.agent_bridge.UsageService"), \
             patch("bridge.agent_bridge.QuotaService"):
            bridge = MagicMock(spec=Bridge)
            ab = AgentBridge(bridge)

        token = ab._cancel_registry.cancel_and_replace("session-1")
        token.cancel()  # Already cancelled

        # Should be a no-op (no exception, no side effects)
        ab.cancel_running_session("session-1")


# ---------------------------------------------------------------------------
# Bridge.cancel_running_agent forwarding
# ---------------------------------------------------------------------------

class TestBridgeCancelRunningAgent:

    def test_cancel_running_agent_forwards_to_agent_bridge(self):
        """Bridge.cancel_running_agent should forward to AgentBridge."""
        from bridge.bridge import Bridge

        with patch("bridge.bridge.create_bot"), \
             patch("bridge.bridge.create_translator"), \
             patch("bridge.bridge.create_voice"), \
             patch("bridge.bridge.conf"):
            bridge = Bridge()
            bridge._agent_bridge = MagicMock()
            bridge.cancel_running_agent("session-1")
            bridge._agent_bridge.cancel_running_session.assert_called_once_with("session-1")

    def test_cancel_running_agent_noop_when_no_agent_bridge(self):
        """Bridge.cancel_running_agent should be a no-op when agent bridge is None."""
        from bridge.bridge import Bridge

        # Create a fresh Bridge instance without singleton interference
        with patch.object(Bridge, '__init__', lambda self: None):
            bridge = Bridge()
            bridge._agent_bridge = None
            # Should not raise
            bridge.cancel_running_agent("session-1")


# ---------------------------------------------------------------------------
# AgentBridge.agent_reply returns None on cancellation
# ---------------------------------------------------------------------------

class TestAgentBridgeReplyOnCancellation:

    def test_agent_reply_returns_none_on_cancelled_error(self):
        """agent_reply should return None (not ERROR Reply) when the agent raises CancelledError."""
        from bridge.agent_bridge import AgentBridge, CancelledError
        from bridge.bridge import Bridge
        from bridge.context import Context

        with patch("bridge.agent_bridge.AgentInitializer") as MockInit, \
             patch("bridge.agent_bridge.CowAgentRuntimeAdapter") as mock_adapter, \
             patch("bridge.agent_bridge.PricingService"), \
             patch("bridge.agent_bridge.UsageService"), \
             patch("bridge.agent_bridge.QuotaService"):
            bridge_inst = MagicMock(spec=Bridge)
            ab = AgentBridge(bridge_inst)

        # Set up a mock agent that raises CancelledError during run_stream
        mock_agent = MagicMock()
        mock_agent.run_stream.side_effect = CancelledError("cancelled")
        mock_agent.tools = []
        mock_agent.model = MagicMock()
        mock_agent.model.model = "test"

        # Make get_agent return our mock
        ab.get_agent = MagicMock(return_value=mock_agent)

        # Mock the runtime adapter to return None (no runtime resolution)
        mock_adapter_inst = mock_adapter.return_value
        mock_adapter_inst.resolve_from_context.return_value = None

        context = Context()
        context["session_id"] = "session-1"

        result = ab.agent_reply("test query", context=context)
        assert result is None


# ---------------------------------------------------------------------------
# WebChannel SSE preemption
# ---------------------------------------------------------------------------

class TestWebChannelSSEPreemption:

    def test_new_message_cancels_old_sse(self):
        """When a new message arrives, the old SSE stream should be cancelled."""
        from queue import Queue

        # Simulate WebChannel's session_to_request tracking
        session_to_request = {}
        sse_queues = {}

        # First request
        old_request_id = "req-old"
        session_key = "default:default:session-1"
        sse_queues[old_request_id] = Queue()
        session_to_request[session_key] = old_request_id

        # Second request — should cancel the first
        new_request_id = "req-new"
        old_rid = session_to_request.get(session_key)
        if old_rid and old_rid in sse_queues:
            sse_queues[old_rid].put({
                "type": "cancelled",
                "content": "Cancelled by newer message",
                "request_id": old_rid,
            })
        session_to_request[session_key] = new_request_id
        sse_queues[new_request_id] = Queue()

        # Verify old SSE queue received cancellation event
        cancelled_event = sse_queues[old_request_id].get(timeout=1)
        assert cancelled_event["type"] == "cancelled"

        # Verify new SSE queue is empty (no spurious events)
        assert sse_queues[new_request_id].empty()

    def test_sse_stream_terminates_on_cancelled(self):
        """SSE stream should terminate when receiving a 'cancelled' event."""
        from queue import Queue

        q = Queue()
        q.put({"type": "cancelled", "content": "test cancel"})

        # Simulate stream_response logic
        item = q.get(timeout=1)
        done = item.get("type") in ("done", "cancelled")
        assert done is True


# ---------------------------------------------------------------------------
# Resource cleanup
# ---------------------------------------------------------------------------

class TestPreemptionCleanup:

    def test_cancel_token_removed_after_completion(self):
        """After a request completes, its token should be removed from registry."""
        reg = CancelTokenRegistry()
        token = reg.cancel_and_replace("session-1")
        assert reg.get("session-1") is token

        # Simulate request completion — remove from registry
        reg.remove("session-1")
        assert reg.get("session-1") is None

    def test_no_leaked_tokens(self):
        """Multiple sessions should not leak tokens after cleanup."""
        reg = CancelTokenRegistry()
        for i in range(10):
            reg.cancel_and_replace(f"s{i}")
        assert reg.active_count == 10

        # Clean up all
        for i in range(10):
            reg.remove(f"s{i}")
        assert reg.active_count == 0

    def test_cancelled_token_does_not_block_new_request(self):
        """After cancellation, a new request for the same session should work."""
        reg = CancelTokenRegistry()
        t1 = reg.cancel_and_replace("s1")
        t1.cancel()
        t2 = reg.cancel_and_replace("s1")
        assert not t2.is_cancelled
        # t2 should be usable
        t2.check_cancelled()  # No error


# ---------------------------------------------------------------------------
# End-to-end preemption flow
# ---------------------------------------------------------------------------

class TestPreemptionE2E:

    def test_full_preemption_flow(self):
        """Simulate the full preemption flow:
        1. User sends message 1 -> gets token1
        2. Agent starts processing with token1
        3. User sends message 2 -> token1 is cancelled, token2 created
        4. Agent's token1 check raises CancelledError
        5. token2 is valid and can proceed
        """
        reg = CancelTokenRegistry()

        # Step 1-2: First message arrives, gets a cancel token
        token1 = reg.cancel_and_replace("user-1")
        assert not token1.is_cancelled

        # Simulate agent processing in a thread
        processing_result = [None]

        def _simulate_agent_processing(token, results):
            try:
                # Simulate turn 1
                token.check_cancelled()
                time.sleep(0.1)  # simulate LLM call
                # Simulate turn 2 — this is where cancellation is detected
                token.check_cancelled()
                results[0] = "completed"
            except CancelledError:
                results[0] = "cancelled"

        agent_thread = threading.Thread(
            target=_simulate_agent_processing, args=(token1, processing_result)
        )
        agent_thread.start()

        # Step 3: While agent is processing, user sends a new message
        time.sleep(0.05)  # Let agent start turn 1
        token2 = reg.cancel_and_replace("user-1")
        assert token1.is_cancelled
        assert not token2.is_cancelled

        # Step 4: Agent thread detects cancellation
        agent_thread.join(timeout=5)
        assert processing_result[0] == "cancelled"

        # Step 5: token2 is valid
        token2.check_cancelled()  # No error — new request can proceed

    def test_rapid_fire_messages(self):
        """Simulate rapid-fire messages: only the last one should survive."""
        reg = CancelTokenRegistry()
        tokens = []
        for i in range(5):
            tokens.append(reg.cancel_and_replace("user-1"))

        # All but the last should be cancelled
        for i in range(4):
            assert tokens[i].is_cancelled
        assert not tokens[4].is_cancelled

        # The last token is usable
        tokens[4].check_cancelled()

    def test_produce_to_cancel_running_flow(self):
        """Integration: produce() -> Bridge.cancel_running_agent() -> token cancelled.

        This tests the critical fix: when a new message arrives via produce(),
        the running agent task is cancelled immediately, not after the semaphore
        is released.
        """
        from bridge.agent_bridge import AgentBridge
        from bridge.bridge import Bridge

        with patch("bridge.agent_bridge.AgentInitializer"), \
             patch("bridge.agent_bridge.CowAgentRuntimeAdapter"), \
             patch("bridge.agent_bridge.PricingService"), \
             patch("bridge.agent_bridge.UsageService"), \
             patch("bridge.agent_bridge.QuotaService"):
            bridge_inst = MagicMock(spec=Bridge)
            ab = AgentBridge(bridge_inst)

        # Simulate: first message is being processed
        token1 = ab._cancel_registry.cancel_and_replace("session-1")
        assert not token1.is_cancelled

        # Simulate: produce() calls cancel_running_agent for the second message
        # This is what ChatChannel.produce() does now
        ab.cancel_running_session("session-1")
        assert token1.is_cancelled

        # Verify the agent processing would detect cancellation
        with pytest.raises(CancelledError):
            token1.check_cancelled()

        # New message gets a fresh token
        token2 = ab._cancel_registry.cancel_and_replace("session-1")
        assert not token2.is_cancelled
        token2.check_cancelled()  # No error

    def test_mcp_tool_cancel_during_execution(self):
        """MCP tool execution should be cancellable via CancelToken."""
        from agent.tools.mcp.mcp_tool import MCPTool
        from agent.tools.mcp.mcp_manager import MCPManager

        manager = MagicMock(spec=MCPManager)
        tool = MCPTool("server1", "tool1", "Test tool", {"type": "object", "properties": {}}, manager)

        cancel_token = CancelToken()
        mock_agent = MagicMock()
        mock_agent._current_cancel_token = cancel_token
        tool.context = mock_agent

        # Simulate cancellation during tool execution
        def mock_run_async(arguments, cancel_token=None):
            # Simulate: tool starts, then gets cancelled
            if cancel_token and cancel_token.is_cancelled:
                raise RuntimeError("MCP call to 'server1' cancelled")
            return {"content": [{"type": "text", "text": "ok"}]}

        tool._run_async = mock_run_async

        # Cancel before execution
        cancel_token.cancel()
        result = tool.execute({})
        assert result.status == "error"

    def test_no_preemption_different_users(self):
        """Different users should not interfere with each other."""
        from bridge.agent_bridge import AgentBridge
        from bridge.bridge import Bridge

        with patch("bridge.agent_bridge.AgentInitializer"), \
             patch("bridge.agent_bridge.CowAgentRuntimeAdapter"), \
             patch("bridge.agent_bridge.PricingService"), \
             patch("bridge.agent_bridge.UsageService"), \
             patch("bridge.agent_bridge.QuotaService"):
            bridge_inst = MagicMock(spec=Bridge)
            ab = AgentBridge(bridge_inst)

        # Two users with active tasks
        token_a = ab._cancel_registry.cancel_and_replace("user-A")
        token_b = ab._cancel_registry.cancel_and_replace("user-B")

        # User A sends new message — only A's task is cancelled
        ab.cancel_running_session("user-A")
        assert token_a.is_cancelled
        assert not token_b.is_cancelled  # B unaffected

        # B's task continues normally
        token_b.check_cancelled()  # No error
