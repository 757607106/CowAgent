from __future__ import annotations

from pathlib import Path

from agent.tools.bash.bash import Bash
from agent.tools.edit.edit import Edit
from agent.tools.ls.ls import Ls
from agent.tools.read.read import Read
from agent.tools.send.send import Send
from agent.tools.write.write import Write


def test_file_tools_reject_absolute_paths_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-a" / "default"
    other_workspace = tmp_path / "tenant-b" / "default"
    workspace.mkdir(parents=True)
    other_workspace.mkdir(parents=True)
    secret = other_workspace / "secret.txt"
    secret.write_text("tenant-b secret", encoding="utf-8")

    tools = [
        Read({"cwd": str(workspace)}),
        Ls({"cwd": str(workspace)}),
        Send({"cwd": str(workspace)}),
        Edit({"cwd": str(workspace)}),
        Write({"cwd": str(workspace)}),
    ]

    read_result = tools[0].execute({"path": str(secret)})
    ls_result = tools[1].execute({"path": str(other_workspace)})
    send_result = tools[2].execute({"path": str(secret)})
    edit_result = tools[3].execute({"path": str(secret), "oldText": "secret", "newText": "changed"})
    write_result = tools[4].execute({"path": str(secret), "content": "changed"})

    for result in [read_result, ls_result, send_result, edit_result, write_result]:
        assert result.status == "error"
        assert "outside workspace" in str(result.result)

    assert secret.read_text(encoding="utf-8") == "tenant-b secret"


def test_file_tools_allow_workspace_relative_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-a" / "default"
    workspace.mkdir(parents=True)

    write_result = Write({"cwd": str(workspace)}).execute({"path": "notes/a.txt", "content": "hello"})
    read_result = Read({"cwd": str(workspace)}).execute({"path": "notes/a.txt"})
    ls_result = Ls({"cwd": str(workspace)}).execute({"path": "notes"})
    edit_result = Edit({"cwd": str(workspace)}).execute(
        {"path": "notes/a.txt", "oldText": "hello", "newText": "hello tenant-a"}
    )
    send_result = Send({"cwd": str(workspace)}).execute({"path": "notes/a.txt"})

    assert write_result.status == "success"
    assert read_result.status == "success"
    assert "hello" in str(read_result.result)
    assert ls_result.status == "success"
    assert "a.txt" in ls_result.result["output"]
    assert edit_result.status == "success"
    assert send_result.status == "success"
    assert send_result.result["path"] == str((workspace / "notes" / "a.txt").resolve())


def test_read_allows_absolute_paths_inside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-a" / "default"
    workspace.mkdir(parents=True)
    note = workspace / "note.txt"
    note.write_text("tenant-a", encoding="utf-8")

    result = Read({"cwd": str(workspace)}).execute({"path": str(note)})

    assert result.status == "success"
    assert "tenant-a" in str(result.result)


def test_bash_rejects_paths_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-a" / "default"
    other_workspace = tmp_path / "tenant-b" / "default"
    workspace.mkdir(parents=True)
    other_workspace.mkdir(parents=True)
    secret = other_workspace / "secret.txt"
    secret.write_text("tenant-b secret", encoding="utf-8")

    result = Bash({"cwd": str(workspace)}).execute({"command": f"cat {secret}"})

    assert result.status == "error"
    assert "outside workspace" in str(result.result)


def test_bash_allows_system_executable_for_workspace_commands(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-a" / "default"
    workspace.mkdir(parents=True)

    result = Bash({"cwd": str(workspace)}).execute({"command": "/bin/pwd"})

    assert result.status == "success"
    assert str(workspace) in result.result["output"]


def test_bash_system_executable_still_rejects_outside_path_args(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-a" / "default"
    other_workspace = tmp_path / "tenant-b" / "default"
    workspace.mkdir(parents=True)
    other_workspace.mkdir(parents=True)
    secret = other_workspace / "secret.txt"
    secret.write_text("tenant-b secret", encoding="utf-8")

    result = Bash({"cwd": str(workspace)}).execute({"command": f"/bin/cat {secret}"})

    assert result.status == "error"
    assert "outside workspace" in str(result.result)


def test_bash_allows_workspace_relative_commands(tmp_path: Path) -> None:
    workspace = tmp_path / "tenant-a" / "default"
    workspace.mkdir(parents=True)
    (workspace / "note.txt").write_text("tenant-a", encoding="utf-8")

    result = Bash({"cwd": str(workspace)}).execute({"command": "cat note.txt"})

    assert result.status == "success"
    assert "tenant-a" in result.result["output"]
