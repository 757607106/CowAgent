"""
Agent Bridge - Integrates Agent system with existing COW bridge
"""

import os
from contextlib import nullcontext
import uuid
from typing import Any, Optional, List

from agent.protocol import Agent, LLMModel, LLMRequest, CancelledError
from agent.protocol.cancel import CancelToken, CancelTokenRegistry
from bridge.agent_event_handler import AgentEventHandler
from bridge.agent_initializer import AgentInitializer
from bridge.bridge import Bridge
from bridge.context import Context
from bridge.reply import Reply, ReplyType
from common import const
from common.log import logger
from common.model_routing import resolve_bot_type_from_model
from common.utils import expand_path
from cow_platform.adapters.cowagent_runtime_adapter import CowAgentRuntimeAdapter
from cow_platform.runtime.scope import get_current_model_config_id, get_current_model_name
from cow_platform.services.pricing_service import PricingService
from cow_platform.services.quota_service import QuotaService
from cow_platform.services.usage_service import UsageService
from models.openai_compatible_bot import OpenAICompatibleBot


def add_openai_compatible_support(bot_instance):
    """
    Dynamically add OpenAI-compatible tool calling support to a bot instance.
    
    This allows any bot to gain tool calling capability without modifying its code,
    as long as it uses OpenAI-compatible API format.
    
    Note: Some bots like ZHIPUAIBot have native tool calling support and don't need enhancement.
    """
    if hasattr(bot_instance, 'call_with_tools'):
        # Bot already has tool calling support (e.g., ZHIPUAIBot)
        logger.debug(f"[AgentBridge] {type(bot_instance).__name__} already has native tool calling support")
        return bot_instance

    # Create a temporary mixin class that combines the bot with OpenAI compatibility
    class EnhancedBot(bot_instance.__class__, OpenAICompatibleBot):
        """Dynamically enhanced bot with OpenAI-compatible tool calling"""

        def get_api_config(self):
            """
            Infer API config from common configuration patterns.
            Most OpenAI-compatible bots use similar configuration.
            """
            from config import conf
            runtime_model = get_current_model_name()

            return {
                'api_key': conf().get("open_ai_api_key"),
                'api_base': conf().get("open_ai_api_base"),
                'model': runtime_model or conf().get("model", "gpt-3.5-turbo"),
                'default_temperature': conf().get("temperature", 0.9),
                'default_top_p': conf().get("top_p", 1.0),
                'default_frequency_penalty': conf().get("frequency_penalty", 0.0),
                'default_presence_penalty': conf().get("presence_penalty", 0.0),
            }

    # Change the bot's class to the enhanced version
    bot_instance.__class__ = EnhancedBot
    logger.info(
        f"[AgentBridge] Enhanced {bot_instance.__class__.__bases__[0].__name__} with OpenAI-compatible tool calling")

    return bot_instance


def _resolve_thinking_enabled(channel_type: str) -> bool:
    from config import conf

    if channel_type != "web":
        return False

    try:
        from cow_platform.runtime.scope import get_current_runtime_context

        runtime_context = get_current_runtime_context()
        if runtime_context is not None and "enable_thinking" in runtime_context.metadata:
            return bool(runtime_context.metadata.get("enable_thinking"))
    except Exception:
        pass

    return bool(conf().get("enable_thinking", True))


class AgentLLMModel(LLMModel):
    """
    LLM Model adapter that uses COW's existing bot infrastructure
    """

    def __init__(self, bridge: Bridge, bot_type: str = "chat"):
        from config import conf
        super().__init__(model=conf().get("model", const.GPT_41))
        self.bridge = bridge
        self.bot_type = bot_type
        self._bot = None
        self._bot_model = None
        self._bot_model_config_id = None

    @property
    def model(self):
        from config import conf

        runtime_model = get_current_model_name()
        if runtime_model:
            return runtime_model
        return conf().get("model", const.GPT_41)

    @model.setter
    def model(self, value):
        pass

    def _resolve_bot_type(self, model_name: str) -> str:
        """Resolve bot type from model name, matching Bridge.__init__ logic."""
        from config import conf

        if conf().get("use_linkai", False) and conf().get("linkai_api_key"):
            return const.LINKAI
        # Support custom bot type configuration
        configured_bot_type = conf().get("bot_type")
        if configured_bot_type:
            return configured_bot_type
       
        return resolve_bot_type_from_model(model_name, default=const.OPENAI)

    @property
    def bot(self):
        """Lazy load the bot, re-create when model or bot_type changes"""
        from models.bot_factory import create_bot
        cur_model = self.model
        cur_bot_type = self._resolve_bot_type(cur_model)
        cur_model_config_id = get_current_model_config_id()
        if (
            self._bot is None
            or self._bot_model != cur_model
            or getattr(self, '_bot_type', None) != cur_bot_type
            or self._bot_model_config_id != cur_model_config_id
        ):
            self._bot = create_bot(cur_bot_type)
            self._bot = add_openai_compatible_support(self._bot)
            self._bot_model = cur_model
            self._bot_type = cur_bot_type
            self._bot_model_config_id = cur_model_config_id
        return self._bot

    def call(self, request: LLMRequest):
        """
        Call the model using COW's bot infrastructure
        """
        try:
            # For non-streaming calls, we'll use the existing reply method
            # This is a simplified implementation
            if hasattr(self.bot, 'call_with_tools'):
                # Use tool-enabled call if available
                kwargs = {
                    'messages': request.messages,
                    'tools': getattr(request, 'tools', None),
                    'stream': False,
                    'model': self.model  # Pass model parameter
                }
                # Only pass max_tokens if it's explicitly set
                if request.max_tokens is not None:
                    kwargs['max_tokens'] = request.max_tokens

                # Extract system prompt if present
                system_prompt = getattr(request, 'system', None)
                if system_prompt:
                    kwargs['system'] = system_prompt

                # Pass context metadata to bot
                channel_type = getattr(self, 'channel_type', None) or ''
                if channel_type:
                    kwargs['channel_type'] = channel_type
                session_id = getattr(self, 'session_id', None)
                if session_id:
                    kwargs['session_id'] = session_id

                thinking_enabled = _resolve_thinking_enabled(channel_type)
                kwargs['thinking'] = {"type": "enabled"} if thinking_enabled else {"type": "disabled"}

                response = self.bot.call_with_tools(**kwargs)
                return self._format_response(response)
            else:
                # Fallback to regular call
                # This would need to be implemented based on your specific needs
                raise NotImplementedError("Regular call not implemented yet")
                
        except Exception as e:
            logger.error(f"AgentLLMModel call error: {e}")
            raise
    
    def call_stream(self, request: LLMRequest):
        """
        Call the model with streaming using COW's bot infrastructure
        """
        try:
            if hasattr(self.bot, 'call_with_tools'):
                # Use tool-enabled streaming call if available
                # Extract system prompt if present
                system_prompt = getattr(request, 'system', None)

                # Build kwargs for call_with_tools
                kwargs = {
                    'messages': request.messages,
                    'tools': getattr(request, 'tools', None),
                    'stream': True,
                    'model': self.model  # Pass model parameter
                }

                # Only pass max_tokens if explicitly set, let the bot use its default
                if request.max_tokens is not None:
                    kwargs['max_tokens'] = request.max_tokens

                # Add system prompt if present
                if system_prompt:
                    kwargs['system'] = system_prompt

                # Pass context metadata to bot
                channel_type = getattr(self, 'channel_type', None) or ''
                if channel_type:
                    kwargs['channel_type'] = channel_type
                session_id = getattr(self, 'session_id', None)
                if session_id:
                    kwargs['session_id'] = session_id

                thinking_enabled = _resolve_thinking_enabled(channel_type)
                kwargs['thinking'] = {"type": "enabled"} if thinking_enabled else {"type": "disabled"}

                stream = self.bot.call_with_tools(**kwargs)
                
                # Convert stream format to our expected format
                for chunk in stream:
                    yield self._format_stream_chunk(chunk)
            else:
                bot_type = type(self.bot).__name__
                raise NotImplementedError(f"Bot {bot_type} does not support call_with_tools. Please add the method.")
                
        except Exception as e:
            logger.error(f"AgentLLMModel call_stream error: {e}", exc_info=True)
            raise
    
    def _format_response(self, response):
        """Format Claude response to our expected format"""
        # This would need to be implemented based on Claude's response format
        return response
    
    def _format_stream_chunk(self, chunk):
        """Format Claude stream chunk to our expected format"""
        # This would need to be implemented based on Claude's stream format
        return chunk


class AgentBridge:
    """
    Bridge class that integrates super Agent with COW
    Manages multiple agent instances per session for conversation isolation
    """
    
    def __init__(self, bridge: Bridge):
        self.bridge = bridge
        self.agents = {}  # session_id -> Agent instance mapping
        self.agent_config_versions = {}
        self.default_agent = None  # For backward compatibility (no session_id)
        self.agent: Optional[Agent] = None
        self.scheduler_initialized = False
        self.runtime_adapter = CowAgentRuntimeAdapter()
        self.pricing_service = PricingService()
        self.usage_service = UsageService(pricing_service=self.pricing_service)
        self.quota_service = QuotaService(usage_service=self.usage_service)

        # Create helper instances
        self.initializer = AgentInitializer(bridge, self)

        # Preemption support: maps session_id -> CancelToken
        self._cancel_registry = CancelTokenRegistry()

    def _check_runtime_quota(self, resolved_runtime, query: str) -> dict:
        """在真实执行前检查当前 Agent 的请求配额。"""
        runtime_context = resolved_runtime.runtime_context
        return self.quota_service.check_request_allowed(
            tenant_id=runtime_context.tenant_id,
            agent_id=runtime_context.agent_id,
            prompt_tokens=self.usage_service.estimate_text_tokens(query),
        )

    def _record_runtime_usage(
        self,
        *,
        resolved_runtime,
        request_id: str,
        query: str,
        completion_text: str,
        model: str,
        channel_type: str,
        status: str,
        agent: Agent | None = None,
        event_handler: AgentEventHandler | None = None,
    ) -> None:
        """记录当前请求的 usage 和成本信息。"""
        runtime_context = resolved_runtime.runtime_context
        provider_usage = self._normalize_provider_usage(getattr(agent, "last_usage", None) if agent else None)
        usage_metrics = event_handler.get_usage_metrics() if event_handler else {}
        skill_names = {
            str(name): 1
            for name in getattr(resolved_runtime.agent_definition, "skills", ())
            if str(name or "").strip()
        }
        metadata = {
            "status": status,
            "tool_names": usage_metrics.get("tool_names", {}),
        }
        if skill_names:
            metadata["skill_names"] = skill_names
        if provider_usage:
            metadata["provider_usage"] = provider_usage
        self.usage_service.record_chat_usage(
            request_id=request_id or f"req_{uuid.uuid4().hex}",
            tenant_id=runtime_context.tenant_id,
            agent_id=runtime_context.agent_id,
            binding_id=str(runtime_context.metadata.get("binding_id", "") or ""),
            session_id=runtime_context.session_id,
            channel_type=channel_type,
            model=model,
            prompt_text=query,
            completion_text=completion_text,
            prompt_tokens=provider_usage.get("prompt_tokens"),
            completion_tokens=provider_usage.get("completion_tokens"),
            token_source="provider" if provider_usage else "estimated",
            tool_call_count=int(usage_metrics.get("tool_call_count", 0)),
            mcp_call_count=int(usage_metrics.get("mcp_call_count", 0)),
            tool_error_count=int(usage_metrics.get("tool_error_count", 0)),
            tool_execution_time_ms=int(usage_metrics.get("tool_execution_time_ms", 0)),
            metadata=metadata,
        )

    @staticmethod
    def _normalize_provider_usage(raw_usage: Any) -> dict[str, int]:
        if not isinstance(raw_usage, dict) or not raw_usage:
            return {}

        def _read_int(*keys: str) -> int | None:
            for key in keys:
                if key not in raw_usage:
                    continue
                value = raw_usage.get(key)
                if value in (None, ""):
                    continue
                try:
                    return max(0, int(value))
                except (TypeError, ValueError):
                    continue
            return None

        prompt_tokens = _read_int("prompt_tokens", "input_tokens", "promptTokenCount")
        completion_tokens = _read_int("completion_tokens", "output_tokens", "candidatesTokenCount")
        total_tokens = _read_int("total_tokens", "totalTokenCount")

        if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
            total_tokens = prompt_tokens + completion_tokens
        if prompt_tokens is None and total_tokens is not None and completion_tokens is not None:
            prompt_tokens = max(0, total_tokens - completion_tokens)
        if completion_tokens is None and total_tokens is not None and prompt_tokens is not None:
            completion_tokens = max(0, total_tokens - prompt_tokens)

        normalized = {}
        if prompt_tokens is not None:
            normalized["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            normalized["completion_tokens"] = completion_tokens
        if total_tokens is not None:
            normalized["total_tokens"] = total_tokens
        return normalized

    def create_agent(self, system_prompt: str, tools: List = None, **kwargs) -> Agent:
        """
        Create the super agent with COW integration
        
        Args:
            system_prompt: System prompt
            tools: List of tools (optional)
            **kwargs: Additional agent parameters
            
        Returns:
            Agent instance
        """
        # Create LLM model that uses COW's bot infrastructure
        model = AgentLLMModel(self.bridge)
        
        # Default tools if none provided
        if tools is None:
            # Use ToolManager to load all available tools
            from agent.tools import ToolManager
            tool_manager = ToolManager()
            tool_manager.load_tools()
            
            tools = []
            workspace_dir = kwargs.get("workspace_dir")
            for tool_name in tool_manager.tool_classes.keys():
                try:
                    tool = tool_manager.create_tool(tool_name)
                    if tool:
                        if workspace_dir and hasattr(tool, 'cwd'):
                            tool.cwd = workspace_dir
                        tools.append(tool)
                except Exception as e:
                    logger.warning(f"[AgentBridge] Failed to load tool {tool_name}: {e}")
        
        # Create agent instance
        agent = Agent(
            system_prompt=system_prompt,
            description=kwargs.get("description", "AI Super Agent"),
            model=model,
            tools=tools,
            max_steps=kwargs.get("max_steps", 15),
            output_mode=kwargs.get("output_mode", "logger"),
            workspace_dir=kwargs.get("workspace_dir"),
            skill_manager=kwargs.get("skill_manager"),
            enable_skills=kwargs.get("enable_skills", True),
            memory_manager=kwargs.get("memory_manager"),
            max_context_tokens=kwargs.get("max_context_tokens"),
            context_reserve_tokens=kwargs.get("context_reserve_tokens"),
            runtime_info=kwargs.get("runtime_info"),
            custom_system_prompt=kwargs.get("custom_system_prompt", ""),
            knowledge_enabled=kwargs.get("knowledge_enabled"),
        )

        # Log skill loading details
        if agent.skill_manager:
            logger.debug(f"[AgentBridge] SkillManager initialized with {len(agent.skill_manager.skills)} skills")

        return agent
    
    def get_agent(self, session_id: str = None, cache_key: str = None, config_version: int | None = None) -> Optional[Agent]:
        """
        Get agent instance for the given session
        
        Args:
            session_id: Session identifier (e.g., user_id). If None, returns default agent.
            cache_key: Agent 实例缓存键，平台模式下会携带 agent_id
        
        Returns:
            Agent instance for this session
        """
        # If no session_id, use default agent (backward compatibility)
        if session_id is None and cache_key is None:
            if self.default_agent is None:
                self._init_default_agent()
            return self.default_agent

        agent_cache_key = cache_key or session_id

        if (
            config_version is not None
            and agent_cache_key in self.agents
            and self.agent_config_versions.get(agent_cache_key) != int(config_version)
        ):
            logger.info(
                f"[AgentBridge] Runtime cache version changed for {agent_cache_key}: "
                f"{self.agent_config_versions.get(agent_cache_key)} -> {int(config_version)}"
            )
            del self.agents[agent_cache_key]
            self.agent_config_versions.pop(agent_cache_key, None)

        # Check if agent exists for this session
        if agent_cache_key not in self.agents:
            self._init_agent_for_session(agent_cache_key, session_id or agent_cache_key)
            if config_version is not None:
                self.agent_config_versions[agent_cache_key] = int(config_version)

        return self.agents[agent_cache_key]
    
    def _init_default_agent(self):
        """Initialize default super agent"""
        agent = self.initializer.initialize_agent(session_id=None)
        self.default_agent = agent
    
    def _init_agent_for_session(self, cache_key: str, session_id: str):
        """Initialize agent for a specific session"""
        agent = self.initializer.initialize_agent(session_id=session_id)
        self.agents[cache_key] = agent
    
    def agent_reply(self, query: str, context: Context = None, 
                   on_event=None, clear_history: bool = False,
                   cancel_token: CancelToken = None) -> Reply:
        """
        Use super agent to reply to a query
        
        Args:
            query: User query
            context: COW context (optional, contains session_id for user isolation)
            on_event: Event callback (optional)
            clear_history: Whether to clear conversation history
            cancel_token: Optional CancelToken for cooperative cancellation
            
        Returns:
            Reply object
        """
        session_id = None
        cache_session_key = None
        agent = None
        resolved_runtime = None
        own_cancel_token = cancel_token is None  # Track if we created the token
        event_handler = None
        effective_session = None
        try:
            # Extract session_id from context for user isolation
            if context:
                session_id = context.kwargs.get("session_id") or context.get("session_id")
                resolved_runtime = self.runtime_adapter.resolve_from_context(context)
                if resolved_runtime:
                    session_id = resolved_runtime.external_session_id
                    cache_session_key = resolved_runtime.cache_session_key

            # Preemption: cancel previous request for this session and get a new token
            effective_session = cache_session_key or session_id or "_default_"
            if cancel_token is None:
                cancel_token = self._cancel_registry.cancel_and_replace(effective_session)
            else:
                # Caller provided their own token; still register for tracking
                with self._cancel_registry._lock:
                    self._cancel_registry._tokens[effective_session] = cancel_token

            # Check if already cancelled before starting work
            cancel_token.check_cancelled()

            runtime_scope = resolved_runtime.activate() if resolved_runtime else nullcontext()

            with runtime_scope:
                if resolved_runtime:
                    quota_result = self._check_runtime_quota(resolved_runtime, query)
                    if not quota_result["allowed"]:
                        logger.warning(f"[AgentBridge] Quota denied: {quota_result['message']}")
                        return Reply(ReplyType.ERROR, quota_result["message"])

                # Get agent for this session (will auto-initialize if needed)
                agent = self.get_agent(
                    session_id=session_id,
                    cache_key=cache_session_key,
                    config_version=resolved_runtime.config_version if resolved_runtime else None,
                )
                if not agent:
                    return Reply(ReplyType.ERROR, "Failed to initialize super agent")
                
                # Create event handler for logging and channel communication
                event_handler = AgentEventHandler(context=context, original_callback=on_event)
                
                # Filter tools based on context
                original_tools = agent.tools
                filtered_tools = original_tools
                
                # If this is a scheduled task execution, exclude scheduler tool to prevent recursion
                if context and context.get("is_scheduled_task"):
                    filtered_tools = [tool for tool in agent.tools if tool.name != "scheduler"]
                    agent.tools = filtered_tools
                    logger.info(f"[AgentBridge] Scheduled task execution: excluded scheduler tool ({len(filtered_tools)}/{len(original_tools)} tools)")
                else:
                    # Attach context to scheduler tool if present
                    if context and agent.tools:
                        for tool in agent.tools:
                            if tool.name == "scheduler":
                                try:
                                    from agent.tools.scheduler.integration import attach_scheduler_to_tool
                                    attach_scheduler_to_tool(tool, context)
                                except Exception as e:
                                    logger.warning(f"[AgentBridge] Failed to attach context to scheduler: {e}")
                                break
                
                # Pass context metadata to model for downstream API requests
                if context and hasattr(agent, 'model'):
                    agent.model.channel_type = context.get("channel_type", "")
                    agent.model.session_id = session_id or ""

                # Store session_id on agent so executor can clear DB on fatal errors
                agent._current_session_id = session_id

                try:
                    # Use agent's run_stream method with event handler and cancel token
                    response = agent.run_stream(
                        user_message=query,
                        on_event=event_handler.handle_event,
                        clear_history=clear_history,
                        cancel_token=cancel_token
                    )
                except CancelledError:
                    logger.info(f"[AgentBridge] Request cancelled for session={session_id}")
                    return None  # Silently drop — the new request will reply
                finally:
                    # Restore original tools
                    if context and context.get("is_scheduled_task"):
                        agent.tools = original_tools

                    # Log execution summary
                    event_handler.log_summary()

                # Persist new messages generated during this run
                if session_id:
                    channel_type = (context.get("channel_type") or "") if context else ""
                    new_messages = getattr(agent, '_last_run_new_messages', [])
                    if new_messages:
                        self._persist_messages(session_id, list(new_messages), channel_type)
                    else:
                        with agent.messages_lock:
                            msg_count = len(agent.messages)
                        if msg_count == 0:
                            try:
                                from agent.memory import get_conversation_store
                                get_conversation_store().clear_session(session_id)
                                logger.info(f"[AgentBridge] Cleared DB for recovered session: {session_id}")
                            except Exception as e:
                                logger.warning(f"[AgentBridge] Failed to clear DB after recovery: {e}")
                
                # Check if there are files to send (from read tool)
                if hasattr(agent, 'stream_executor') and hasattr(agent.stream_executor, 'files_to_send'):
                    files_to_send = agent.stream_executor.files_to_send
                    if files_to_send:
                        # Send the first file (for now, handle one file at a time)
                        file_info = files_to_send[0]
                        logger.info(f"[AgentBridge] Sending file: {file_info.get('path')}")
                        
                        # Clear files_to_send for next request
                        agent.stream_executor.files_to_send = []

                        if resolved_runtime and context:
                            self._record_runtime_usage(
                                resolved_runtime=resolved_runtime,
                                request_id=context.get("request_id", "") or "",
                                query=query,
                                completion_text=response or "",
                                model=getattr(agent.model, "model", "") or "",
                                channel_type=(context.get("channel_type") or ""),
                                status="success",
                                agent=agent,
                                event_handler=event_handler,
                            )

                        # Return file reply based on file type
                        return self._create_file_reply(file_info, response, context)

                if resolved_runtime and context:
                    self._record_runtime_usage(
                        resolved_runtime=resolved_runtime,
                        request_id=context.get("request_id", "") or "",
                        query=query,
                        completion_text=response or "",
                        model=getattr(agent.model, "model", "") or "",
                        channel_type=(context.get("channel_type") or ""),
                        status="success",
                        agent=agent,
                        event_handler=event_handler,
                    )

                return Reply(ReplyType.TEXT, response)
            
        except CancelledError:
            logger.info(f"[AgentBridge] Request cancelled for session={session_id}")
            return None  # Silently drop — the new request will reply
        except Exception as e:
            logger.error(f"Agent reply error: {e}")
            if resolved_runtime and context:
                try:
                    self._record_runtime_usage(
                        resolved_runtime=resolved_runtime,
                        request_id=context.get("request_id", "") or "",
                        query=query,
                        completion_text=str(e),
                        model=(getattr(agent.model, "model", "") if agent else "") or "",
                        channel_type=(context.get("channel_type") or ""),
                        status="error",
                        agent=agent,
                        event_handler=event_handler,
                    )
                except Exception as usage_err:
                    logger.warning(f"[AgentBridge] Failed to record usage after error: {usage_err}")
            # If the agent cleared its messages due to format error / overflow,
            # also purge the DB so the next request starts clean.
            cleanup_scope = resolved_runtime.activate() if resolved_runtime else nullcontext()
            with cleanup_scope:
                if session_id and agent:
                    try:
                        with agent.messages_lock:
                            msg_count = len(agent.messages)
                        if msg_count == 0:
                            from agent.memory import get_conversation_store
                            get_conversation_store().clear_session(session_id)
                            logger.info(f"[AgentBridge] Cleared DB for session after error: {session_id}")
                    except Exception as db_err:
                        logger.warning(f"[AgentBridge] Failed to clear DB after error: {db_err}")
            return Reply(ReplyType.ERROR, f"Agent error: {str(e)}")
        finally:
            # Clean up cancel token registry entry when execution completes
            if own_cancel_token and effective_session is not None:
                self._cancel_registry.remove(effective_session)
    
    def _create_file_reply(self, file_info: dict, text_response: str, context: Context = None) -> Reply:
        """
        Create a reply for sending files
        
        Args:
            file_info: File metadata from read tool
            text_response: Text response from agent
            context: Context object
            
        Returns:
            Reply object for file sending
        """
        file_type = file_info.get("file_type", "file")
        file_path = file_info.get("path")
        
        # For images, use IMAGE_URL type (channel will handle upload)
        if file_type == "image":
            # Convert local path to file:// URL for channel processing
            file_url = f"file://{file_path}"
            logger.info(f"[AgentBridge] Sending image: {file_url}")
            reply = Reply(ReplyType.IMAGE_URL, file_url)
            # Attach text message if present (for channels that support text+image)
            if text_response:
                reply.text_content = text_response  # Store accompanying text
            return reply
        
        # For all file types (document, video, audio), use FILE type
        if file_type in ["document", "video", "audio"]:
            file_url = f"file://{file_path}"
            logger.info(f"[AgentBridge] Sending {file_type}: {file_url}")
            reply = Reply(ReplyType.FILE, file_url)
            reply.file_name = file_info.get("file_name", os.path.basename(file_path))
            # Attach text message if present
            if text_response:
                reply.text_content = text_response
            return reply
        
        # For all other file types (tar.gz, zip, etc.), also use FILE type
        file_url = f"file://{file_path}"
        logger.info(f"[AgentBridge] Sending generic file: {file_url}")
        reply = Reply(ReplyType.FILE, file_url)
        reply.file_name = file_info.get("file_name", os.path.basename(file_path))
        if text_response:
            reply.text_content = text_response
        return reply
    
    def _migrate_config_to_env(self, workspace_root: str):
        """
        Sync API keys from config.json to .env file.
        Adds new keys and updates changed values on each startup.

        Args:
            workspace_root: Workspace directory path (not used, kept for compatibility)
        """
        from config import conf
        import os

        if conf().get("web_tenant_auth", True):
            logger.debug("[AgentBridge] Skip global .env sync in platform tenant mode")
            return
        
        key_mapping = {
            "open_ai_api_key": "OPENAI_API_KEY",
            "open_ai_api_base": "OPENAI_API_BASE",
            "gemini_api_key": "GEMINI_API_KEY",
            "claude_api_key": "CLAUDE_API_KEY",
            "linkai_api_key": "LINKAI_API_KEY",
        }
        
        env_file = expand_path("~/.cow/.env")
        
        # Read existing env vars (key -> value)
        existing_env_vars = {}
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, val = line.split('=', 1)
                            existing_env_vars[key.strip()] = val.strip()
            except Exception as e:
                logger.warning(f"[AgentBridge] Failed to read .env file: {e}")
        
        # Sync config.json values into .env (add/update/remove)
        updated = False
        for config_key, env_key in key_mapping.items():
            raw = conf().get(config_key, "")
            value = raw.strip() if raw else ""
            old_value = existing_env_vars.get(env_key)

            if value:
                if old_value == value:
                    continue
                existing_env_vars[env_key] = value
                os.environ[env_key] = value
                updated = True
            else:
                if old_value is None:
                    continue
                existing_env_vars.pop(env_key, None)
                os.environ.pop(env_key, None)
                updated = True

        if updated:
            try:
                env_dir = os.path.dirname(env_file)
                os.makedirs(env_dir, exist_ok=True)

                with open(env_file, 'w', encoding='utf-8') as f:
                    f.write('# Environment variables for agent\n')
                    f.write('# Auto-managed - synced from config.json on startup\n\n')
                    for key, value in sorted(existing_env_vars.items()):
                        f.write(f'{key}={value}\n')

                logger.info(f"[AgentBridge] Synced API keys from config.json to .env")
            except Exception as e:
                logger.warning(f"[AgentBridge] Failed to sync API keys: {e}")
    
    def _persist_messages(
        self, session_id: str, new_messages: list, channel_type: str = ""
    ) -> None:
        """
        Persist new messages to the conversation store after each agent run.

        Failures are logged but never propagate — they must not interrupt replies.
        """
        if not new_messages:
            return
        try:
            from config import conf
            if not conf().get("conversation_persistence", True):
                return
        except Exception:
            pass
        try:
            from agent.memory import get_conversation_store
            get_conversation_store().append_messages(
                session_id, new_messages, channel_type=channel_type
            )
        except Exception as e:
            logger.warning(
                f"[AgentBridge] Failed to persist messages for session={session_id}: {e}"
            )

    def cancel_running_session(self, session_id: str, *, cache_key: str = "", context: Context = None):
        """Cancel the currently running agent task for a session.

        Called by ChatChannel.produce() when a new message arrives so that the
        in-flight request is cooperatively interrupted, without waiting for
        the semaphore-locked handler to finish first.

        Args:
            session_id: The session whose running task should be cancelled.
        """
        effective_session = cache_key or ""
        if not effective_session and context is not None:
            try:
                resolved_runtime = self.runtime_adapter.resolve_from_context(context)
                if resolved_runtime:
                    effective_session = resolved_runtime.cache_session_key
            except Exception as e:
                logger.debug(f"[AgentBridge] Failed to resolve scoped cancel key: {e}")
        effective_session = effective_session or session_id or "_default_"
        token = self._cancel_registry.get(effective_session)
        if token is not None and not token.is_cancelled:
            token.cancel()
            logger.info(f"[AgentBridge] Cancelled running task for session={effective_session}")

    def clear_session(self, session_id: str = None, cache_key: str = None):
        """
        Clear a specific session's agent and conversation history
        
        Args:
            session_id: Session identifier to clear
            cache_key: 平台模式下的实例缓存键
        """
        target_key = cache_key or session_id
        if target_key in self.agents:
            logger.info(f"[AgentBridge] Clearing session: {target_key}")
            del self.agents[target_key]
            self.agent_config_versions.pop(target_key, None)

    def clear_agent_sessions(self, tenant_id: str, agent_id: str):
        """
        Clear all cached runtime sessions for a specific tenant-agent pair.

        Args:
            tenant_id: Tenant identifier
            agent_id: Agent identifier
        """
        from cow_platform.runtime.namespaces import build_namespace

        prefix = build_namespace(tenant_id, agent_id) + ":"
        matched_keys = [key for key in list(self.agents.keys()) if str(key).startswith(prefix)]
        if not matched_keys:
            return
        for key in matched_keys:
            del self.agents[key]
            self.agent_config_versions.pop(key, None)
        logger.info(
            f"[AgentBridge] Cleared {len(matched_keys)} cached session(s) for "
            f"tenant={tenant_id}, agent={agent_id}"
        )
    
    def clear_all_sessions(self):
        """Clear all agent sessions"""
        logger.info(f"[AgentBridge] Clearing all sessions ({len(self.agents)} total)")
        self.agents.clear()
        self.agent_config_versions.clear()
        self.default_agent = None
    
    def refresh_all_skills(self) -> int:
        """
        Refresh skills and conditional tools in all agent instances after
        environment variable changes. This allows hot-reload without restarting.

        Returns:
            Number of agent instances refreshed
        """
        import os
        from dotenv import load_dotenv
        from config import conf

        # Reload environment variables from .env file
        workspace_root = expand_path(conf().get("agent_workspace", "~/cow"))
        env_file = os.path.join(workspace_root, '.env')

        if os.path.exists(env_file):
            load_dotenv(env_file, override=True)
            logger.info(f"[AgentBridge] Reloaded environment variables from {env_file}")

        refreshed_count = 0

        # Collect all agent instances to refresh
        agents_to_refresh = []
        if self.default_agent:
            agents_to_refresh.append(("default", self.default_agent))
        for session_id, agent in self.agents.items():
            agents_to_refresh.append((session_id, agent))

        for label, agent in agents_to_refresh:
            # Refresh skills
            if hasattr(agent, 'skill_manager') and agent.skill_manager:
                agent.skill_manager.refresh_skills()

            # Refresh conditional tools (e.g. web_search depends on API keys)
            self._refresh_conditional_tools(agent)

            refreshed_count += 1

        if refreshed_count > 0:
            logger.info(f"[AgentBridge] Refreshed skills & tools in {refreshed_count} agent instance(s)")

        return refreshed_count

    @staticmethod
    def _refresh_conditional_tools(agent):
        """
        Add or remove conditional tools based on current environment variables.
        For example, web_search should only be present when BOCHA_API_KEY or
        LINKAI_API_KEY is set.
        """
        try:
            from agent.tools.web_search.web_search import WebSearch

            has_tool = any(t.name == "web_search" for t in agent.tools)
            available = WebSearch.is_available()

            if available and not has_tool:
                # API key was added - inject the tool
                tool = WebSearch()
                tool.model = agent.model
                agent.tools.append(tool)
                logger.info("[AgentBridge] web_search tool added (API key now available)")
            elif not available and has_tool:
                # API key was removed - remove the tool
                agent.tools = [t for t in agent.tools if t.name != "web_search"]
                logger.info("[AgentBridge] web_search tool removed (API key no longer available)")
        except Exception as e:
            logger.debug(f"[AgentBridge] Failed to refresh conditional tools: {e}")
