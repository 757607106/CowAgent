"""
Conversation history persistence using PostgreSQL.

The public API intentionally mirrors the former local store so the bridge,
channels, and web console keep using the same calls while storage is centralized
and isolated by tenant_id + agent_id + session_id.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.log import logger
from cow_platform.db import connect, jsonb


DEFAULT_MAX_AGE_DAYS: int = 30


def _is_visible_user_message(content: Any) -> bool:
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        return any(isinstance(b, dict) and b.get("type") == "text" for b in content)
    return False


def _extract_display_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        return "\n".join(p for p in parts if p).strip()
    return ""


def _extract_tool_results(content: Any) -> Dict[str, str]:
    if not isinstance(content, list):
        return {}
    results = {}
    for b in content:
        if not isinstance(b, dict) or b.get("type") != "tool_result":
            continue
        tool_id = b.get("tool_use_id", "")
        result_content = b.get("content", "")
        if isinstance(result_content, list):
            result_content = "\n".join(
                rb.get("text", "")
                for rb in result_content
                if isinstance(rb, dict) and rb.get("type") == "text"
            )
        results[tool_id] = str(result_content)
    return results


def _decode_content(raw_content: Any) -> Any:
    if isinstance(raw_content, str):
        try:
            return json.loads(raw_content)
        except Exception:
            return raw_content
    return raw_content


def _group_into_display_turns(rows: List[tuple]) -> List[Dict[str, Any]]:
    groups: List[tuple] = []
    cur_user: Optional[tuple] = None
    cur_rest: List[tuple] = []
    started = False

    for role, raw_content, created_at in rows:
        content = _decode_content(raw_content)
        if role == "user" and _is_visible_user_message(content):
            if started:
                groups.append((cur_user, cur_rest))
            cur_user = (content, created_at)
            cur_rest = []
            started = True
        else:
            cur_rest.append((role, content, created_at))

    if started:
        groups.append((cur_user, cur_rest))

    turns: List[Dict[str, Any]] = []
    for user_row, rest in groups:
        if user_row:
            content, created_at = user_row
            text = _extract_display_text(content)
            if text:
                turns.append({"role": "user", "content": text, "created_at": created_at})

        steps: List[Dict[str, Any]] = []
        tool_results: Dict[str, str] = {}
        final_text = ""
        final_ts: Optional[int] = None

        for role, content, created_at in rest:
            if role == "user":
                tool_results.update(_extract_tool_results(content))
            elif role == "assistant":
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        btype = block.get("type")
                        if btype == "thinking":
                            txt = block.get("thinking", "").strip()
                            if txt:
                                steps.append({"type": "thinking", "content": txt})
                        elif btype == "text":
                            txt = block.get("text", "").strip()
                            if txt:
                                steps.append({"type": "content", "content": txt})
                                final_text = txt
                        elif btype == "tool_use":
                            steps.append(
                                {
                                    "type": "tool",
                                    "id": block.get("id", ""),
                                    "name": block.get("name", ""),
                                    "arguments": block.get("input", {}),
                                }
                            )
                elif isinstance(content, str) and content.strip():
                    steps.append({"type": "content", "content": content.strip()})
                    final_text = content.strip()
                final_ts = created_at

        for step in steps:
            if step["type"] == "tool":
                step["result"] = tool_results.get(step.get("id", ""), "")

        if steps or final_text:
            turns.append(
                {
                    "role": "assistant",
                    "content": final_text,
                    "steps": steps,
                    "created_at": final_ts or (user_row[1] if user_row else 0),
                }
            )

    return turns


class ConversationStore:
    """PostgreSQL-backed per-agent conversation history store."""

    def __init__(self, tenant_id: str = "legacy", agent_id: str = "default"):
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self._lock = threading.Lock()

    def load_messages(self, session_id: str, max_turns: int = 30) -> List[Dict[str, Any]]:
        with self._lock:
            with connect() as conn:
                ctx_row = conn.execute(
                    """
                    SELECT context_start_seq
                    FROM platform_conversation_sessions
                    WHERE tenant_id = %s AND agent_id = %s AND session_id = %s
                    """,
                    (self.tenant_id, self.agent_id, session_id),
                ).fetchone()
                ctx_start = ctx_row["context_start_seq"] if ctx_row else 0
                rows = conn.execute(
                    """
                    SELECT seq, role, content
                    FROM platform_conversation_messages
                    WHERE tenant_id = %s AND agent_id = %s
                      AND session_id = %s AND seq >= %s
                    ORDER BY seq DESC
                    """,
                    (self.tenant_id, self.agent_id, session_id, ctx_start),
                ).fetchall()

        if not rows:
            return []

        visible_turn_seqs: List[int] = []
        for row in rows:
            if row["role"] != "user":
                continue
            content = _decode_content(row["content"])
            if _is_visible_user_message(content):
                visible_turn_seqs.append(row["seq"])

        cutoff_seq = None if len(visible_turn_seqs) <= max_turns else visible_turn_seqs[max_turns - 1]

        result = []
        for row in reversed(rows):
            if cutoff_seq is not None and row["seq"] < cutoff_seq:
                continue
            content = _decode_content(row["content"])
            if row["role"] == "assistant" and isinstance(content, list):
                content = [b for b in content if b.get("type") != "thinking"]
            result.append({"role": row["role"], "content": content})
        return result

    def append_messages(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        channel_type: str = "",
    ) -> None:
        if not messages:
            return

        now = int(time.time())
        with self._lock:
            with connect() as conn:
                with conn.transaction():
                    conn.execute(
                        """
                        INSERT INTO platform_conversation_sessions
                            (tenant_id, agent_id, session_id, channel_type,
                             created_at, last_active, msg_count)
                        VALUES (%s, %s, %s, %s, %s, %s, 0)
                        ON CONFLICT (tenant_id, agent_id, session_id)
                        DO UPDATE SET last_active = EXCLUDED.last_active
                        """,
                        (self.tenant_id, self.agent_id, session_id, channel_type, now, now),
                    )
                    conn.execute(
                        """
                        SELECT session_id
                        FROM platform_conversation_sessions
                        WHERE tenant_id = %s AND agent_id = %s AND session_id = %s
                        FOR UPDATE
                        """,
                        (self.tenant_id, self.agent_id, session_id),
                    ).fetchone()
                    row = conn.execute(
                        """
                        SELECT COALESCE(MAX(seq), -1) AS max_seq
                        FROM platform_conversation_messages
                        WHERE tenant_id = %s AND agent_id = %s AND session_id = %s
                        """,
                        (self.tenant_id, self.agent_id, session_id),
                    ).fetchone()
                    next_seq = int(row["max_seq"]) + 1

                    for msg in messages:
                        conn.execute(
                            """
                            INSERT INTO platform_conversation_messages
                                (tenant_id, agent_id, session_id, seq, role, content, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (tenant_id, agent_id, session_id, seq) DO NOTHING
                            """,
                            (
                                self.tenant_id,
                                self.agent_id,
                                session_id,
                                next_seq,
                                msg.get("role", ""),
                                jsonb(msg.get("content", "")),
                                now,
                            ),
                        )
                        next_seq += 1

                    conn.execute(
                        """
                        UPDATE platform_conversation_sessions s
                        SET msg_count = (
                            SELECT COUNT(*)
                            FROM platform_conversation_messages m
                            WHERE m.tenant_id = s.tenant_id
                              AND m.agent_id = s.agent_id
                              AND m.session_id = s.session_id
                        )
                        WHERE tenant_id = %s AND agent_id = %s AND session_id = %s
                        """,
                        (self.tenant_id, self.agent_id, session_id),
                    )
                    title_row = conn.execute(
                        """
                        SELECT title
                        FROM platform_conversation_sessions
                        WHERE tenant_id = %s AND agent_id = %s AND session_id = %s
                        """,
                        (self.tenant_id, self.agent_id, session_id),
                    ).fetchone()
                    if title_row and not title_row["title"]:
                        for msg in messages:
                            if msg.get("role") != "user":
                                continue
                            text = _extract_display_text(msg.get("content", ""))
                            if text:
                                conn.execute(
                                    """
                                    UPDATE platform_conversation_sessions
                                    SET title = %s
                                    WHERE tenant_id = %s AND agent_id = %s AND session_id = %s
                                    """,
                                    (text[:50].split("\n")[0], self.tenant_id, self.agent_id, session_id),
                                )
                                break

    def clear_context(self, session_id: str) -> int:
        with self._lock:
            with connect() as conn:
                with conn.transaction():
                    row = conn.execute(
                        """
                        SELECT COALESCE(MAX(seq), -1) AS max_seq
                        FROM platform_conversation_messages
                        WHERE tenant_id = %s AND agent_id = %s AND session_id = %s
                        """,
                        (self.tenant_id, self.agent_id, session_id),
                    ).fetchone()
                    new_start = int(row["max_seq"]) + 1
                    conn.execute(
                        """
                        UPDATE platform_conversation_sessions
                        SET context_start_seq = %s
                        WHERE tenant_id = %s AND agent_id = %s AND session_id = %s
                        """,
                        (new_start, self.tenant_id, self.agent_id, session_id),
                    )
                    return new_start

    def get_context_start_seq(self, session_id: str) -> int:
        with self._lock:
            with connect() as conn:
                row = conn.execute(
                    """
                    SELECT context_start_seq
                    FROM platform_conversation_sessions
                    WHERE tenant_id = %s AND agent_id = %s AND session_id = %s
                    """,
                    (self.tenant_id, self.agent_id, session_id),
                ).fetchone()
        return int(row["context_start_seq"]) if row else 0

    def clear_session(self, session_id: str) -> None:
        with self._lock:
            with connect() as conn:
                conn.execute(
                    """
                    DELETE FROM platform_conversation_sessions
                    WHERE tenant_id = %s AND agent_id = %s AND session_id = %s
                    """,
                    (self.tenant_id, self.agent_id, session_id),
                )
                conn.commit()

    def cleanup_old_sessions(self, max_age_days: Optional[int] = None) -> int:
        try:
            from config import conf

            max_age = max_age_days or conf().get("conversation_max_age_days", DEFAULT_MAX_AGE_DAYS)
        except Exception:
            max_age = max_age_days or DEFAULT_MAX_AGE_DAYS

        cutoff = int(time.time()) - max_age * 86400
        with self._lock:
            with connect() as conn:
                rows = conn.execute(
                    """
                    DELETE FROM platform_conversation_sessions
                    WHERE tenant_id = %s AND agent_id = %s
                      AND last_active < %s AND channel_type != 'web'
                    RETURNING session_id
                    """,
                    (self.tenant_id, self.agent_id, cutoff),
                ).fetchall()
                conn.commit()
        deleted = len(rows)
        if deleted:
            logger.info(f"[ConversationStore] Pruned {deleted} expired sessions")
        return deleted

    def load_history_page(
        self,
        session_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        page = max(1, page)
        with self._lock:
            with connect() as conn:
                ctx_row = conn.execute(
                    """
                    SELECT context_start_seq
                    FROM platform_conversation_sessions
                    WHERE tenant_id = %s AND agent_id = %s AND session_id = %s
                    """,
                    (self.tenant_id, self.agent_id, session_id),
                ).fetchone()
                ctx_start = int(ctx_row["context_start_seq"]) if ctx_row else 0
                rows = conn.execute(
                    """
                    SELECT seq, role, content, created_at
                    FROM platform_conversation_messages
                    WHERE tenant_id = %s AND agent_id = %s AND session_id = %s
                    ORDER BY seq ASC
                    """,
                    (self.tenant_id, self.agent_id, session_id),
                ).fetchall()

        plain_rows = [(row["role"], row["content"], row["created_at"]) for row in rows]
        visible = _group_into_display_turns(plain_rows)

        visible_user_seqs: List[int] = []
        for row in rows:
            if row["role"] != "user":
                continue
            content = _decode_content(row["content"])
            if _is_visible_user_message(content):
                visible_user_seqs.append(row["seq"])

        user_turn_idx = 0
        for turn in visible:
            if turn["role"] == "user" and user_turn_idx < len(visible_user_seqs):
                turn["_seq"] = visible_user_seqs[user_turn_idx]
                user_turn_idx += 1

        total = len(visible)
        offset = (page - 1) * page_size
        page_items = list(reversed(visible))[offset : offset + page_size]
        page_items = list(reversed(page_items))

        return {
            "messages": page_items,
            "context_start_seq": ctx_start,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": offset + page_size < total,
        }

    def list_sessions(
        self,
        channel_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        page = max(1, page)
        offset = (page - 1) * page_size
        conditions = ["tenant_id = %s", "agent_id = %s"]
        params: list[Any] = [self.tenant_id, self.agent_id]
        if channel_type:
            conditions.append("channel_type = %s")
            params.append(channel_type)
        where = " AND ".join(conditions)
        with self._lock:
            with connect() as conn:
                total = conn.execute(
                    f"SELECT COUNT(*) AS cnt FROM platform_conversation_sessions WHERE {where}",
                    tuple(params),
                ).fetchone()["cnt"]
                rows = conn.execute(
                    f"""
                    SELECT session_id, title, created_at, last_active, msg_count
                    FROM platform_conversation_sessions
                    WHERE {where}
                    ORDER BY last_active DESC
                    LIMIT %s OFFSET %s
                    """,
                    (*params, page_size, offset),
                ).fetchall()

        sessions = [
            {
                "session_id": row["session_id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "last_active": row["last_active"],
                "msg_count": row["msg_count"],
            }
            for row in rows
        ]
        return {
            "sessions": sessions,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": offset + page_size < total,
        }

    def rename_session(self, session_id: str, title: str) -> bool:
        with self._lock:
            with connect() as conn:
                cursor = conn.execute(
                    """
                    UPDATE platform_conversation_sessions
                    SET title = %s
                    WHERE tenant_id = %s AND agent_id = %s AND session_id = %s
                    """,
                    (title, self.tenant_id, self.agent_id, session_id),
                )
                conn.commit()
                return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            with connect() as conn:
                total_sessions = conn.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM platform_conversation_sessions
                    WHERE tenant_id = %s AND agent_id = %s
                    """,
                    (self.tenant_id, self.agent_id),
                ).fetchone()["cnt"]
                total_messages = conn.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM platform_conversation_messages
                    WHERE tenant_id = %s AND agent_id = %s
                    """,
                    (self.tenant_id, self.agent_id),
                ).fetchone()["cnt"]
                by_channel = conn.execute(
                    """
                    SELECT channel_type, COUNT(*) AS cnt
                    FROM platform_conversation_sessions
                    WHERE tenant_id = %s AND agent_id = %s
                    GROUP BY channel_type
                    ORDER BY cnt DESC
                    """,
                    (self.tenant_id, self.agent_id),
                ).fetchall()
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "by_channel": {row["channel_type"] or "unknown": row["cnt"] for row in by_channel},
        }


_store_instances: Dict[str, ConversationStore] = {}
_store_lock = threading.Lock()


def _scope_from_workspace(workspace_root: Optional[str]) -> tuple[str, str]:
    if not workspace_root:
        return "legacy", "default"
    workspace = str(Path(workspace_root).expanduser().resolve())
    digest = hashlib.sha256(workspace.encode("utf-8")).hexdigest()[:16]
    return "workspace", digest


def _resolve_scope(workspace_root: Optional[str] = None, db_path: Optional[Path] = None) -> tuple[str, str]:
    try:
        from cow_platform.runtime.scope import get_current_runtime_context

        runtime_context = get_current_runtime_context()
        if runtime_context is not None:
            return runtime_context.tenant_id, runtime_context.agent_id
    except Exception:
        pass

    if db_path is not None:
        digest = hashlib.sha256(str(Path(db_path)).encode("utf-8")).hexdigest()[:16]
        return "dbpath", digest
    return _scope_from_workspace(workspace_root)


def get_conversation_store(
    workspace_root: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> ConversationStore:
    tenant_id, agent_id = _resolve_scope(workspace_root=workspace_root, db_path=db_path)
    store_key = f"{tenant_id}:{agent_id}"
    if store_key in _store_instances:
        return _store_instances[store_key]

    with _store_lock:
        if store_key in _store_instances:
            return _store_instances[store_key]
        _store_instances[store_key] = ConversationStore(tenant_id=tenant_id, agent_id=agent_id)
        logger.debug(f"[ConversationStore] Using PostgreSQL scope: {store_key}")
        return _store_instances[store_key]


def reset_conversation_store_cache() -> None:
    with _store_lock:
        _store_instances.clear()
