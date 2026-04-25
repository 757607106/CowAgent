from __future__ import annotations

import os
import time
from pathlib import Path
from types import MappingProxyType
from typing import Any

from psycopg import errors

from common.utils import expand_path
from config import conf
from cow_platform.db import connect, jsonb
from cow_platform.domain.models import AgentDefinition
from cow_platform.runtime.namespaces import build_workspace_path


def get_legacy_workspace_root() -> Path:
    env_workspace = os.getenv("AGENT_WORKSPACE") or os.getenv("agent_workspace")
    if env_workspace:
        return Path(expand_path(env_workspace))
    return Path(expand_path(conf().get("agent_workspace", "~/cow")))


def get_platform_data_root() -> Path:
    return get_legacy_workspace_root() / "platform"


def get_platform_workspace_root() -> Path:
    return get_legacy_workspace_root() / "workspaces"


class PostgresAgentRepository:
    """PostgreSQL-backed Agent repository."""

    def list_agents(self, tenant_id: str) -> list[AgentDefinition]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT tenant_id, agent_id, name, version, model, model_config_id, system_prompt,
                       metadata, tools, skills, knowledge_enabled, mcp_servers
                FROM platform_agents
                WHERE tenant_id = %s
                ORDER BY agent_id, name
                """,
                (tenant_id,),
            ).fetchall()
        return [self._to_definition(row) for row in rows]

    def get_agent(self, tenant_id: str, agent_id: str) -> AgentDefinition | None:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT tenant_id, agent_id, name, version, model, model_config_id, system_prompt,
                       metadata, tools, skills, knowledge_enabled, mcp_servers
                FROM platform_agents
                WHERE tenant_id = %s AND agent_id = %s
                """,
                (tenant_id, agent_id),
            ).fetchone()
        return self._to_definition(row) if row else None

    def create_agent(
        self,
        tenant_id: str,
        agent_id: str,
        name: str,
        model: str = "",
        model_config_id: str = "",
        system_prompt: str = "",
        metadata: dict[str, Any] | None = None,
        tools: tuple[str, ...] | list[str] | None = None,
        skills: tuple[str, ...] | list[str] | None = None,
        knowledge_enabled: bool = False,
        mcp_servers: dict[str, Any] | None = None,
    ) -> AgentDefinition:
        now = int(time.time())
        tools_list = list(tools or [])
        skills_list = list(skills or [])
        metadata_obj = metadata or {}
        mcp_obj = mcp_servers or {}
        versions = [
            {
                "version": 1,
                "name": name,
                "model": model,
                "model_config_id": model_config_id,
                "system_prompt": system_prompt,
                "metadata": metadata_obj,
                "tools": tools_list,
                "skills": skills_list,
                "knowledge_enabled": bool(knowledge_enabled),
                "mcp_servers": mcp_obj,
                "updated_at": now,
            }
        ]
        try:
            with connect() as conn:
                row = conn.execute(
                    """
                    INSERT INTO platform_agents
                        (tenant_id, agent_id, name, version, model, model_config_id, system_prompt,
                         metadata, tools, skills, knowledge_enabled, mcp_servers,
                         versions, created_at, updated_at)
                    VALUES (%s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING tenant_id, agent_id, name, version, model, model_config_id, system_prompt,
                              metadata, tools, skills, knowledge_enabled, mcp_servers
                    """,
                    (
                        tenant_id,
                        agent_id,
                        name,
                        model,
                        model_config_id,
                        system_prompt,
                        jsonb(metadata_obj),
                        jsonb(tools_list),
                        jsonb(skills_list),
                        bool(knowledge_enabled),
                        jsonb(mcp_obj),
                        jsonb(versions),
                        now,
                        now,
                    ),
                ).fetchone()
                conn.commit()
        except errors.UniqueViolation as exc:
            raise ValueError(f"agent already exists: {agent_id}") from exc
        return self._to_definition(row)

    def update_agent(
        self,
        tenant_id: str,
        agent_id: str,
        *,
        name: str | None = None,
        model: str | None = None,
        model_config_id: str | None = None,
        system_prompt: str | None = None,
        metadata: dict[str, Any] | None = None,
        tools: tuple[str, ...] | list[str] | None = None,
        skills: tuple[str, ...] | list[str] | None = None,
        knowledge_enabled: bool | None = None,
        mcp_servers: dict[str, Any] | None = None,
    ) -> AgentDefinition:
        current = self.export_record_by_id(tenant_id, agent_id)
        version = int(current.get("version", 1)) + 1
        next_record = {
            "name": current["name"] if name is None else name,
            "model": current.get("model", "") if model is None else model,
            "model_config_id": current.get("model_config_id", "") if model_config_id is None else model_config_id,
            "system_prompt": current.get("system_prompt", "") if system_prompt is None else system_prompt,
            "metadata": current.get("metadata", {}) if metadata is None else metadata,
            "tools": current.get("tools", []) if tools is None else list(tools),
            "skills": current.get("skills", []) if skills is None else list(skills),
            "knowledge_enabled": current.get("knowledge_enabled", False)
            if knowledge_enabled is None
            else bool(knowledge_enabled),
            "mcp_servers": current.get("mcp_servers", {}) if mcp_servers is None else mcp_servers,
        }
        now = int(time.time())
        versions = list(current.get("versions") or [])
        versions.append(
            {
                "version": version,
                **next_record,
                "updated_at": now,
            }
        )
        with connect() as conn:
            row = conn.execute(
                """
                UPDATE platform_agents
                SET name = %s, version = %s, model = %s, model_config_id = %s, system_prompt = %s,
                    metadata = %s, tools = %s, skills = %s, knowledge_enabled = %s,
                    mcp_servers = %s, versions = %s, updated_at = %s
                WHERE tenant_id = %s AND agent_id = %s
                RETURNING tenant_id, agent_id, name, version, model, model_config_id, system_prompt,
                          metadata, tools, skills, knowledge_enabled, mcp_servers
                """,
                (
                    next_record["name"],
                    version,
                    next_record["model"],
                    next_record["model_config_id"],
                    next_record["system_prompt"],
                    jsonb(next_record["metadata"]),
                    jsonb(next_record["tools"]),
                    jsonb(next_record["skills"]),
                    next_record["knowledge_enabled"],
                    jsonb(next_record["mcp_servers"]),
                    jsonb(versions),
                    now,
                    tenant_id,
                    agent_id,
                ),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"agent not found: {agent_id}")
        return self._to_definition(row)

    def get_workspace_path(self, tenant_id: str, agent_id: str) -> Path:
        return build_workspace_path(get_platform_workspace_root(), tenant_id, agent_id)

    def export_record(self, definition: AgentDefinition) -> dict[str, Any]:
        try:
            return self.export_record_by_id(definition.tenant_id, definition.agent_id)
        except KeyError:
            record = {
                "tenant_id": definition.tenant_id,
                "agent_id": definition.agent_id,
                "name": definition.name,
                "version": definition.version,
                "model": definition.model,
                "model_config_id": definition.model_config_id,
                "system_prompt": definition.system_prompt,
                "metadata": dict(definition.metadata) if definition.metadata else {},
                "tools": list(definition.tools),
                "skills": list(definition.skills),
                "knowledge_enabled": definition.knowledge_enabled,
                "mcp_servers": dict(definition.mcp_servers) if definition.mcp_servers else {},
                "versions": [],
                "created_at": None,
                "updated_at": None,
            }
            record["workspace_path"] = str(self.get_workspace_path(definition.tenant_id, definition.agent_id))
            return record

    def export_record_by_id(self, tenant_id: str, agent_id: str) -> dict[str, Any]:
        with connect() as conn:
            row = conn.execute(
                """
                SELECT tenant_id, agent_id, name, version, model, model_config_id, system_prompt,
                       metadata, tools, skills, knowledge_enabled, mcp_servers,
                       versions, created_at, updated_at
                FROM platform_agents
                WHERE tenant_id = %s AND agent_id = %s
                """,
                (tenant_id, agent_id),
            ).fetchone()
        if not row:
            raise KeyError(f"agent not found: {agent_id}")
        record = dict(row)
        record["workspace_path"] = str(self.get_workspace_path(tenant_id, agent_id))
        return record

    def delete_agent(self, tenant_id: str, agent_id: str) -> AgentDefinition:
        with connect() as conn:
            row = conn.execute(
                """
                DELETE FROM platform_agents
                WHERE tenant_id = %s AND agent_id = %s
                RETURNING tenant_id, agent_id, name, version, model, model_config_id, system_prompt,
                          metadata, tools, skills, knowledge_enabled, mcp_servers
                """,
                (tenant_id, agent_id),
            ).fetchone()
            conn.commit()
        if not row:
            raise KeyError(f"agent not found: {agent_id}")
        return self._to_definition(row)

    @staticmethod
    def _to_definition(record: dict[str, Any]) -> AgentDefinition:
        return AgentDefinition(
            tenant_id=record["tenant_id"],
            agent_id=record["agent_id"],
            name=record["name"],
            version=int(record.get("version", 1)),
            model=record.get("model", ""),
            model_config_id=record.get("model_config_id", ""),
            system_prompt=record.get("system_prompt", ""),
            metadata=record.get("metadata", {}) or {},
            tools=tuple(record.get("tools", []) or []),
            skills=tuple(record.get("skills", []) or []),
            knowledge_enabled=bool(record.get("knowledge_enabled", False)),
            mcp_servers=MappingProxyType(record.get("mcp_servers", {}) or {}),
        )


AgentRepository = PostgresAgentRepository
