from agent.tools.memory.memory_get import MemoryGetTool


class _DummyConfig:
    def __init__(self, workspace):
        self._workspace = workspace

    def get_workspace(self):
        return self._workspace


class _DummyMemoryManager:
    def __init__(self, workspace):
        self.config = _DummyConfig(workspace)


def test_missing_daily_memory_file_is_not_a_tool_error(tmp_path):
    tool = MemoryGetTool(_DummyMemoryManager(tmp_path))

    result = tool.execute({"path": "memory/2026-04-23.md"})

    assert result.status == "success"
    assert "no detailed daily memory file" in result.result
    assert "MEMORY.md" in result.result


def test_missing_non_daily_memory_file_still_fails(tmp_path):
    tool = MemoryGetTool(_DummyMemoryManager(tmp_path))

    result = tool.execute({"path": "memory/missing-note.md"})

    assert result.status == "error"
    assert "File not found" in result.result
