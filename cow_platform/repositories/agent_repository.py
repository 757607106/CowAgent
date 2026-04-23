from __future__ import annotations

import json
import os
import threading
import time
from types import MappingProxyType
from pathlib import Path
from typing import Any

from common.utils import expand_path
from config import conf

from cow_platform.domain.models import AgentDefinition
from cow_platform.runtime.namespaces import build_workspace_path


def get_legacy_workspace_root() -> Path:
    """获取 legacy 模式下的工作空间根目录。"""
    env_workspace = os.getenv("AGENT_WORKSPACE") or os.getenv("agent_workspace")
    if env_workspace:
        return Path(expand_path(env_workspace))
    return Path(expand_path(conf().get("agent_workspace", "~/cow")))


def get_platform_data_root() -> Path:
    """获取平台元数据目录。"""
    return get_legacy_workspace_root() / "platform"


def get_platform_workspace_root() -> Path:
    """获取平台 Agent 工作区根目录。"""
    return get_legacy_workspace_root() / "workspaces"


class FileAgentRepository:
    """基于 JSON 文件的 Agent 仓储。"""

    def __init__(self, store_path: Path | None = None):
        self.store_path = store_path or (get_platform_data_root() / "agents.json")
        self._lock = threading.Lock()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def list_agents(self, tenant_id: str) -> list[AgentDefinition]:
        with self._lock:
            store = self._load_store()
        definitions = []
        for record in store.get("agents", {}).values():
            if record.get("tenant_id") != tenant_id:
                continue
            definitions.append(self._to_definition(record))
        definitions.sort(key=lambda item: (item.agent_id, item.name))
        return definitions

    def get_agent(self, tenant_id: str, agent_id: str) -> AgentDefinition | None:
        with self._lock:
            store = self._load_store()
            record = store.get("agents", {}).get(self._build_key(tenant_id, agent_id))
        if not record:
            return None
        return self._to_definition(record)

    def create_agent(
        self,
        tenant_id: str,
        agent_id: str,
        name: str,
        model: str = "",
        system_prompt: str = "",
        metadata: dict[str, Any] | None = None,
        tools: tuple[str, ...] | list[str] | None = None,
        skills: tuple[str, ...] | list[str] | None = None,
        knowledge_enabled: bool = False,
        mcp_servers: dict[str, Any] | None = None,
    ) -> AgentDefinition:
        now = int(time.time())
        key = self._build_key(tenant_id, agent_id)
        tools_tuple = tuple(tools) if tools else ()
        skills_tuple = tuple(skills) if skills else ()
        with self._lock:
            store = self._load_store()
            if key in store["agents"]:
                raise ValueError(f"agent already exists: {agent_id}")

            record = {
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "name": name,
                "version": 1,
                "model": model,
                "system_prompt": system_prompt,
                "metadata": metadata or {},
                "tools": list(tools_tuple),
                "skills": list(skills_tuple),
                "knowledge_enabled": knowledge_enabled,
                "mcp_servers": mcp_servers or {},
                "created_at": now,
                "updated_at": now,
                "versions": [
                    {
                        "version": 1,
                        "name": name,
                        "model": model,
                        "system_prompt": system_prompt,
                        "metadata": metadata or {},
                        "tools": list(tools_tuple),
                        "skills": list(skills_tuple),
                        "knowledge_enabled": knowledge_enabled,
                        "mcp_servers": mcp_servers or {},
                        "updated_at": now,
                    }
                ],
            }
            store["agents"][key] = record
            self._save_store(store)
        return self._to_definition(record)

    def update_agent(
        self,
        tenant_id: str,
        agent_id: str,
        *,
        name: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        metadata: dict[str, Any] | None = None,
        tools: tuple[str, ...] | list[str] | None = None,
        skills: tuple[str, ...] | list[str] | None = None,
        knowledge_enabled: bool | None = None,
        mcp_servers: dict[str, Any] | None = None,
    ) -> AgentDefinition:
        now = int(time.time())
        key = self._build_key(tenant_id, agent_id)
        with self._lock:
            store = self._load_store()
            record = store["agents"].get(key)
            if not record:
                raise KeyError(f"agent not found: {agent_id}")

            record["version"] = int(record.get("version", 0)) + 1
            if name is not None:
                record["name"] = name
            if model is not None:
                record["model"] = model
            if system_prompt is not None:
                record["system_prompt"] = system_prompt
            if metadata is not None:
                record["metadata"] = metadata
            if tools is not None:
                record["tools"] = list(tools)
            if skills is not None:
                record["skills"] = list(skills)
            if knowledge_enabled is not None:
                record["knowledge_enabled"] = knowledge_enabled
            if mcp_servers is not None:
                record["mcp_servers"] = mcp_servers
            record["updated_at"] = now
            record.setdefault("versions", []).append(
                {
                    "version": record["version"],
                    "name": record["name"],
                    "model": record.get("model", ""),
                    "system_prompt": record.get("system_prompt", ""),
                    "metadata": record.get("metadata", {}),
                    "tools": record.get("tools", []),
                    "skills": record.get("skills", []),
                    "knowledge_enabled": record.get("knowledge_enabled", False),
                    "mcp_servers": record.get("mcp_servers", {}),
                    "updated_at": now,
                }
            )
            self._save_store(store)
        return self._to_definition(record)

    def get_workspace_path(self, tenant_id: str, agent_id: str) -> Path:
        return build_workspace_path(get_platform_workspace_root(), tenant_id, agent_id)

    def export_record(self, definition: AgentDefinition) -> dict[str, Any]:
        """导出给接口层使用的完整记录。"""
        record = {
            "tenant_id": definition.tenant_id,
            "agent_id": definition.agent_id,
            "name": definition.name,
            "version": definition.version,
            "model": definition.model,
            "system_prompt": definition.system_prompt,
            "metadata": dict(definition.metadata) if definition.metadata else {},
            "tools": list(definition.tools),
            "skills": list(definition.skills),
            "knowledge_enabled": definition.knowledge_enabled,
            "mcp_servers": dict(definition.mcp_servers) if definition.mcp_servers else {},
        }
        record["workspace_path"] = str(self.get_workspace_path(definition.tenant_id, definition.agent_id))
        with self._lock:
            store = self._load_store()
            saved = store.get("agents", {}).get(self._build_key(definition.tenant_id, definition.agent_id), {})
        record["versions"] = saved.get("versions", [])
        record["created_at"] = saved.get("created_at")
        record["updated_at"] = saved.get("updated_at")
        return record

    def _build_key(self, tenant_id: str, agent_id: str) -> str:
        return f"{tenant_id}:{agent_id}"

    def _load_store(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return {"agents": {}}
        with self.store_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if "agents" not in data:
            data["agents"] = {}
        return data

    def _save_store(self, store: dict[str, Any]) -> None:
        with self.store_path.open("w", encoding="utf-8") as file:
            json.dump(store, file, ensure_ascii=False, indent=2)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> AgentDefinition:
        mcp_raw = record.get("mcp_servers", {}) or {}
        return AgentDefinition(
            tenant_id=record["tenant_id"],
            agent_id=record["agent_id"],
            name=record["name"],
            version=int(record.get("version", 1)),
            model=record.get("model", ""),
            system_prompt=record.get("system_prompt", ""),
            metadata=record.get("metadata", {}) or {},
            tools=tuple(record.get("tools", []) or []),
            skills=tuple(record.get("skills", []) or []),
            knowledge_enabled=bool(record.get("knowledge_enabled", False)),
            mcp_servers=MappingProxyType(mcp_raw),
        )
