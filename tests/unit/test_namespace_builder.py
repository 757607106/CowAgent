from pathlib import Path

import pytest

from cow_platform.runtime.namespaces import (
    build_namespace,
    build_session_temp_path,
    build_workspace_path,
    normalize_namespace_segment,
)


def test_normalize_namespace_segment_replaces_unsafe_characters() -> None:
    assert normalize_namespace_segment(" tenant / one :prod ") == "tenant-one-prod"


def test_build_namespace_joins_normalized_segments() -> None:
    assert build_namespace("tenant / one", "agent:blue", "memory") == "tenant-one:agent-blue:memory"


def test_workspace_and_session_paths_are_namespaced(tmp_path: Path) -> None:
    workspace = build_workspace_path(tmp_path / "workspaces", "tenant a", "agent/main")
    session_temp = build_session_temp_path(tmp_path / "tmp", "tenant a", "agent/main", "session:01")

    assert workspace == tmp_path / "workspaces" / "tenant-a" / "agent-main"
    assert session_temp == tmp_path / "tmp" / "tenant-a" / "agent-main" / "session-01"


def test_namespace_segment_cannot_be_blank() -> None:
    with pytest.raises(ValueError):
        normalize_namespace_segment("   ")
