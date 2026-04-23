from __future__ import annotations

import re
from pathlib import Path


_NON_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def normalize_namespace_segment(value: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("namespace segment must not be empty")
    normalized = _NON_SAFE_CHARS.sub("-", text).strip("-")
    if not normalized:
        raise ValueError("namespace segment must contain at least one safe character")
    return normalized


def build_namespace(*parts: str) -> str:
    normalized_parts = [normalize_namespace_segment(part) for part in parts]
    return ":".join(normalized_parts)


def build_workspace_path(root: str | Path, tenant_id: str, agent_id: str) -> Path:
    return Path(root) / normalize_namespace_segment(tenant_id) / normalize_namespace_segment(agent_id)


def build_session_temp_path(
    root: str | Path,
    tenant_id: str,
    agent_id: str,
    session_id: str,
) -> Path:
    return (
        Path(root)
        / normalize_namespace_segment(tenant_id)
        / normalize_namespace_segment(agent_id)
        / normalize_namespace_segment(session_id)
    )
