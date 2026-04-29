from __future__ import annotations

import json
import os
import time

import web

from common.log import logger
from channel.web.handlers.dependencies import (
    WebChannel,
    _generate_session_title,
    _get_mcp_server_service,
    _get_runtime_adapter,
    _get_session_repository,
    _get_session_store,
    _get_workspace_root,
    _is_knowledge_enabled,
    _parse_bool,
    _require_auth,
    _require_platform_admin,
    _require_tenant_manage,
    _resolve_runtime_target,
    _scope_tenant_id,
)

class ToolsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.tools.tool_manager import ToolManager
            tm = ToolManager()
            if not tm.tool_classes:
                tm.load_tools()
            tools = []
            for name, cls in tm.tool_classes.items():
                try:
                    instance = cls()
                    tools.append({
                        "name": name,
                        "description": instance.description,
                    })
                except Exception:
                    tools.append({"name": name, "description": ""})
            try:
                from agent.tools.memory.memory_search import MemorySearchTool
                from agent.tools.memory.memory_get import MemoryGetTool
                existing_names = {item.get("name") for item in tools}
                for cls in (MemorySearchTool, MemoryGetTool):
                    if cls.name not in existing_names:
                        tools.append({
                            "name": cls.name,
                            "description": cls.description,
                        })
            except Exception as e:
                logger.debug(f"[WebChannel] Memory tool metadata unavailable: {e}")
            return json.dumps({"status": "success", "tools": tools}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Tools API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class SkillsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.skills.service import SkillService
            from agent.skills.manager import SkillManager
            params = web.input(agent_id='', binding_id='', tenant_id='')
            workspace_root = _get_workspace_root(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            manager = SkillManager(custom_dir=os.path.join(workspace_root, "skills"))
            service = SkillService(manager)
            skills = service.query()
            return json.dumps({"status": "success", "skills": skills}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Skills API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.skills.service import SkillService
            from agent.skills.manager import SkillManager
            body = json.loads(web.data())
            action = body.get("action")
            name = body.get("name")
            if not action or not name:
                return json.dumps({"status": "error", "message": "action and name are required"})
            workspace_root = _get_workspace_root(
                agent_id=body.get("agent_id", ""),
                tenant_id=body.get("tenant_id", ""),
                binding_id=body.get("binding_id", ""),
            )
            manager = SkillManager(custom_dir=os.path.join(workspace_root, "skills"))
            service = SkillService(manager)
            if action == "open":
                service.open({"name": name})
            elif action == "close":
                service.close({"name": name})
            elif action == "delete":
                service.delete({"name": name})
            else:
                return json.dumps({"status": "error", "message": f"unknown action: {action}"})
            return json.dumps({"status": "success"}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Skills POST error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class MemoryHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.memory.service import MemoryService
            params = web.input(page='1', page_size='20', category='memory', agent_id='', binding_id='', tenant_id='')
            workspace_root = _get_workspace_root(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            service = MemoryService(workspace_root)
            result = service.list_files(
                page=int(params.page), page_size=int(params.page_size),
                category=params.category,
            )
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Memory API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class MemoryContentHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.memory.service import MemoryService
            params = web.input(filename='', category='memory', agent_id='', binding_id='', tenant_id='')
            if not params.filename:
                return json.dumps({"status": "error", "message": "filename required"})
            workspace_root = _get_workspace_root(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            service = MemoryService(workspace_root)
            result = service.get_content(params.filename, category=params.category)
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except ValueError:
            return json.dumps({"status": "error", "message": "invalid filename"})
        except FileNotFoundError:
            return json.dumps({"status": "error", "message": "file not found"})
        except Exception as e:
            logger.error(f"[WebChannel] Memory content API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class SchedulerHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(agent_id='', binding_id='', tenant_id='')
            target = _resolve_runtime_target(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            tasks = None
            try:
                from cow_platform.services.scheduler_task_store import PlatformSchedulerTaskStore

                store = PlatformSchedulerTaskStore().for_scope(
                    tenant_id=target["tenant_id"],
                    agent_id=target["agent_id"] or "default",
                    binding_id=target["binding_id"],
                )
                tasks = store.list_tasks()
            except Exception:
                from agent.tools.scheduler.task_store import TaskStore

                workspace_root = _get_workspace_root(
                    agent_id=params.agent_id,
                    tenant_id=params.tenant_id,
                    binding_id=params.binding_id,
                )
                store_path = os.path.join(workspace_root, "scheduler", "tasks.json")
                store = TaskStore(store_path)
                tasks = store.list_tasks()
            return json.dumps({"status": "success", "tasks": tasks}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Scheduler API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class SessionsHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(page='1', page_size='50', agent_id='', binding_id='', tenant_id='')
            target = _resolve_runtime_target(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            if target["agent_id"]:
                repository = _get_session_repository()
                result = repository.list_sessions(
                    tenant_id=target["tenant_id"],
                    agent_id=target["agent_id"],
                    channel_type="web",
                    page=int(params.page),
                    page_size=int(params.page_size),
                )
            else:
                store = _get_session_store()
                result = store.list_sessions(
                    channel_type="web",
                    page=int(params.page),
                    page_size=int(params.page_size),
                )
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Sessions API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class SessionDetailHandler:
    def DELETE(self, session_id: str):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        logger.info(f"[WebChannel] DELETE session request: {session_id}")
        try:
            if not session_id:
                return json.dumps({"status": "error", "message": "session_id required"})
            params = web.input(agent_id='', binding_id='', tenant_id='')
            target = _resolve_runtime_target(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            tenant_id = target["tenant_id"]
            agent_id = target["agent_id"]

            if agent_id:
                repository = _get_session_repository()
                repository.clear_session(tenant_id, agent_id, session_id)
            else:
                _get_session_store().clear_session(session_id)

            # Also remove the Agent instance from AgentBridge if exists
            try:
                from bridge.bridge import Bridge
                ab = Bridge().get_agent_bridge()
                if agent_id:
                    cache_key = _get_runtime_adapter().build_cache_session_key(tenant_id, agent_id, session_id)
                    ab.clear_session(session_id=session_id, cache_key=cache_key)
                    logger.info(f"[WebChannel] Removed agent instance for session {cache_key}")
                else:
                    ab.clear_session(session_id=session_id)
                    logger.info(f"[WebChannel] Removed agent instance for session {session_id}")
            except Exception:
                pass

            channel = WebChannel()
            channel.session_queues.pop(channel._build_scoped_session_key(session_id, agent_id, tenant_id), None)

            logger.info(f"[WebChannel] Session deleted: {session_id}")
            return json.dumps({"status": "success"})
        except Exception as e:
            logger.error(f"[WebChannel] Session delete error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def PUT(self, session_id: str):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            if not session_id:
                return json.dumps({"status": "error", "message": "session_id required"})
            body = json.loads(web.data())
            title = body.get("title", "").strip()
            if not title:
                return json.dumps({"status": "error", "message": "title required"})
            target = _resolve_runtime_target(
                agent_id=body.get("agent_id", ""),
                tenant_id=body.get("tenant_id", ""),
                binding_id=body.get("binding_id", ""),
            )

            if target["agent_id"]:
                repository = _get_session_repository()
                found = repository.rename_session(target["tenant_id"], target["agent_id"], session_id, title)
            else:
                found = _get_session_store().rename_session(session_id, title)
            if not found:
                return json.dumps({"status": "error", "message": "session not found"})
            return json.dumps({"status": "success"})
        except Exception as e:
            logger.error(f"[WebChannel] Session rename error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class SessionTitleHandler:
    def POST(self, session_id: str):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            if not session_id:
                return json.dumps({"status": "error", "message": "session_id required"})

            body = json.loads(web.data())
            user_message = body.get("user_message", "")
            assistant_reply = body.get("assistant_reply", "")
            target = _resolve_runtime_target(
                agent_id=body.get("agent_id", ""),
                tenant_id=body.get("tenant_id", ""),
                binding_id=body.get("binding_id", ""),
            )
            if not user_message:
                return json.dumps({"status": "error", "message": "user_message required"})

            title = _generate_session_title(user_message, assistant_reply)

            if target["agent_id"]:
                repository = _get_session_repository()
                updated = repository.rename_session(target["tenant_id"], target["agent_id"], session_id, title)
            else:
                updated = _get_session_store().rename_session(session_id, title)
            logger.info(f"[WebChannel] Session title set: sid={session_id}, title='{title}', db_updated={updated}")

            return json.dumps({"status": "success", "title": title}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Title generation error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class SessionClearContextHandler:
    def POST(self, session_id: str):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            if not session_id:
                return json.dumps({"status": "error", "message": "session_id required"})
            params = web.input(agent_id='', binding_id='', tenant_id='')
            target = _resolve_runtime_target(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            tenant_id = target["tenant_id"]
            agent_id = target["agent_id"]

            if agent_id:
                repository = _get_session_repository()
                new_seq = repository.clear_context(tenant_id, agent_id, session_id)
            else:
                new_seq = _get_session_store().clear_context(session_id)

            # Delete the agent instance so a fresh one is created on the next message
            try:
                from bridge.bridge import Bridge
                bridge = Bridge()
                ab = bridge.get_agent_bridge()
                if agent_id:
                    cache_key = _get_runtime_adapter().build_cache_session_key(tenant_id, agent_id, session_id)
                    ab.clear_session(session_id=session_id, cache_key=cache_key)
                    logger.info(f"[WebChannel] Cleared agent instance for session {cache_key}")
                else:
                    ab.clear_session(session_id=session_id)
                    logger.info(f"[WebChannel] Cleared agent instance for session {session_id}")
            except Exception:
                pass

            return json.dumps({"status": "success", "context_start_seq": new_seq})
        except Exception as e:
            logger.error(f"[WebChannel] Clear context error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class HistoryHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        web.header('Access-Control-Allow-Origin', '*')
        try:
            params = web.input(session_id='', page='1', page_size='20', agent_id='', binding_id='', tenant_id='')
            session_id = params.session_id.strip()
            if not session_id:
                return json.dumps({"status": "error", "message": "session_id required"})
            target = _resolve_runtime_target(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            if target["agent_id"]:
                repository = _get_session_repository()
                result = repository.load_history_page(
                    tenant_id=target["tenant_id"],
                    agent_id=target["agent_id"],
                    session_id=session_id,
                    page=int(params.page),
                    page_size=int(params.page_size),
                )
            else:
                store = _get_session_store()
                result = store.load_history_page(
                    session_id=session_id,
                    page=int(params.page),
                    page_size=int(params.page_size),
                )
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] History API error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class LogsHandler:
    def GET(self):
        _require_platform_admin()
        web.header('Content-Type', 'text/event-stream; charset=utf-8')
        web.header('Cache-Control', 'no-cache')
        web.header('X-Accel-Buffering', 'no')

        from config import get_root
        log_path = os.path.join(get_root(), "run.log")

        def generate():
            if not os.path.isfile(log_path):
                yield b"data: {\"type\": \"error\", \"message\": \"run.log not found\"}\n\n"
                return

            # Read last 200 lines for initial display
            try:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                tail_lines = lines[-200:]
                chunk = ''.join(tail_lines)
                payload = json.dumps({"type": "init", "content": chunk}, ensure_ascii=False)
                yield f"data: {payload}\n\n".encode('utf-8')
            except Exception as e:
                yield f"data: {{\"type\": \"error\", \"message\": \"{e}\"}}\n\n".encode('utf-8')
                return

            # Tail new lines
            try:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    f.seek(0, 2)  # seek to end
                    deadline = time.time() + 600  # 10 min max
                    while time.time() < deadline:
                        line = f.readline()
                        if line:
                            payload = json.dumps({"type": "line", "content": line}, ensure_ascii=False)
                            yield f"data: {payload}\n\n".encode('utf-8')
                        else:
                            yield b": keepalive\n\n"
                            time.sleep(1)
            except GeneratorExit:
                return
            except Exception:
                return

        return generate()

class KnowledgeListHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.knowledge.service import KnowledgeService
            params = web.input(agent_id='', binding_id='', tenant_id='')
            knowledge_enabled = _is_knowledge_enabled(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            svc = KnowledgeService(
                _get_workspace_root(
                    agent_id=params.agent_id,
                    tenant_id=params.tenant_id,
                    binding_id=params.binding_id,
                ),
                enabled=knowledge_enabled,
            )
            result = svc.list_tree()
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Knowledge list error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class KnowledgeReadHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.knowledge.service import KnowledgeService
            params = web.input(path='', agent_id='', binding_id='', tenant_id='')
            knowledge_enabled = _is_knowledge_enabled(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            svc = KnowledgeService(
                _get_workspace_root(
                    agent_id=params.agent_id,
                    tenant_id=params.tenant_id,
                    binding_id=params.binding_id,
                ),
                enabled=knowledge_enabled,
            )
            result = svc.read_file(params.path)
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except (ValueError, FileNotFoundError, RuntimeError) as e:
            return json.dumps({"status": "error", "message": str(e)})
        except Exception as e:
            logger.error(f"[WebChannel] Knowledge read error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class KnowledgeGraphHandler:
    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            from agent.knowledge.service import KnowledgeService
            params = web.input(agent_id='', binding_id='', tenant_id='')
            knowledge_enabled = _is_knowledge_enabled(
                agent_id=params.agent_id,
                tenant_id=params.tenant_id,
                binding_id=params.binding_id,
            )
            svc = KnowledgeService(
                _get_workspace_root(
                    agent_id=params.agent_id,
                    tenant_id=params.tenant_id,
                    binding_id=params.binding_id,
                ),
                enabled=knowledge_enabled,
            )
            return json.dumps(svc.build_graph(), ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] Knowledge graph error: {e}")
            return json.dumps({"nodes": [], "links": [], "enabled": False})

class MCPServersHandler:
    """Tenant-level MCP server configuration collection."""

    def GET(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='')
            tenant_id = _scope_tenant_id(params.tenant_id)
            servers = _get_mcp_server_service().list_servers(tenant_id)
            return json.dumps({"status": "success", "servers": servers}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] MCP servers list error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def POST(self):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "")).strip())
            server = _get_mcp_server_service().save_server(
                tenant_id=tenant_id,
                name=str(body.get("name", "")).strip(),
                command=str(body.get("command", "")).strip(),
                args=body.get("args", []),
                env=body.get("env", {}),
                enabled=_parse_bool(body.get("enabled", True), True),
                metadata=body.get("metadata", {}),
            )
            return json.dumps({"status": "success", "server": server}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] MCP server create error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class MCPServerDetailHandler:
    """Tenant-level MCP server configuration detail."""

    def PUT(self, server_name):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data() or "{}")
            tenant_id = _scope_tenant_id(str(body.get("tenant_id", "")).strip())
            server = _get_mcp_server_service().save_server(
                tenant_id=tenant_id,
                name=server_name,
                command=str(body.get("command", "")).strip(),
                args=body.get("args", []),
                env=body.get("env", {}),
                enabled=_parse_bool(body.get("enabled", True), True),
                metadata=body.get("metadata", {}),
            )
            return json.dumps({"status": "success", "server": server}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] MCP server update error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

    def DELETE(self, server_name):
        _require_tenant_manage()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='')
            tenant_id = _scope_tenant_id(params.tenant_id)
            server = _get_mcp_server_service().delete_server(tenant_id=tenant_id, name=server_name)
            return json.dumps({"status": "success", "server": server, "name": server_name}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] MCP server delete error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class MCPServersTestHandler:
    """POST /api/mcp/servers/test — test connectivity to an MCP server."""

    def POST(self):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            body = json.loads(web.data())
            command = body.get("command", "")
            args = body.get("args", [])
            env = body.get("env", None)

            if not command:
                return json.dumps({"status": "error", "message": "command is required"})

            import asyncio
            from agent.tools.mcp.mcp_manager import MCPManager
            manager = MCPManager()
            result = asyncio.run(manager.test_connection(command, args, env))
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] MCP server test error: {e}")
            return json.dumps({"status": "error", "message": str(e)})

class MCPServerToolsHandler:
    """GET /api/mcp/servers/{name}/tools — list tools from a specific MCP server."""

    def GET(self, server_name):
        _require_auth()
        web.header('Content-Type', 'application/json; charset=utf-8')
        try:
            params = web.input(tenant_id='')
            tenant_id = _scope_tenant_id(params.tenant_id)

            server = _get_mcp_server_service().get_server(tenant_id, server_name)
            if not server.enabled:
                return json.dumps({
                    "status": "error",
                    "message": f"MCP server '{server_name}' is disabled",
                })

            import asyncio
            from agent.tools.mcp.mcp_manager import MCPManager

            manager = MCPManager()
            result = asyncio.run(manager.test_connection(
                command=server.command,
                args=list(server.args),
                env=dict(server.env),
            ))
            if not result.get("success"):
                return json.dumps({
                    "status": "error",
                    "message": result.get("error") or f"MCP server '{server_name}' not available",
                    "tools": [],
                }, ensure_ascii=False)
            tool_list = result.get("tools", [])
            return json.dumps({"status": "success", "tools": tool_list}, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[WebChannel] MCP server tools error: {e}")
            return json.dumps({"status": "error", "message": str(e)})


__all__ = ["ToolsHandler", "SkillsHandler", "MemoryHandler", "MemoryContentHandler", "SchedulerHandler", "SessionsHandler", "SessionDetailHandler", "SessionTitleHandler", "SessionClearContextHandler", "HistoryHandler", "LogsHandler", "KnowledgeListHandler", "KnowledgeReadHandler", "KnowledgeGraphHandler", "MCPServersHandler", "MCPServerDetailHandler", "MCPServersTestHandler", "MCPServerToolsHandler"]
