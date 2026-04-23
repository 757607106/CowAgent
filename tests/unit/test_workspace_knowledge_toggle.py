from pathlib import Path

import pytest

from agent.knowledge.service import KnowledgeService
from agent.prompt.workspace import ensure_workspace


def test_workspace_does_not_create_knowledge_dir_when_disabled(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace-disabled"

    ensure_workspace(str(workspace_dir), knowledge_enabled=False)

    assert not (workspace_dir / "knowledge").exists()
    rule_text = (workspace_dir / "RULE.md").read_text(encoding="utf-8")
    assert "## 知识系统" not in rule_text
    assert "knowledge/" not in rule_text


def test_knowledge_service_hides_disabled_knowledge_base(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace-knowledge"
    knowledge_dir = workspace_dir / "knowledge" / "notes"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    (knowledge_dir / "a.md").write_text("# A\ncontent", encoding="utf-8")

    service = KnowledgeService(str(workspace_dir), enabled=False)

    assert service.list_tree() == {
        "tree": [],
        "stats": {"pages": 0, "size": 0},
        "enabled": False,
    }
    assert service.build_graph() == {"nodes": [], "links": [], "enabled": False}

    with pytest.raises(RuntimeError, match="knowledge is disabled"):
        service.read_file("notes/a.md")
