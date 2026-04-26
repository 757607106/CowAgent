"""Workspace path guards shared by file-capable tools."""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

from common.utils import expand_path


ACCESS_DENIED_MESSAGE = "Error: Access denied: path outside workspace"

_URL_RE = re.compile(r"https?://\S+")
_ABS_OR_HOME_PATH_RE = re.compile(r"(?<![\w.:-])(?:~(?:/[^\s'\";|&<>(){}$`]*)?|/(?:[^\s'\";|&<>(){}$`]*)?)")


class WorkspaceAccessError(ValueError):
    """Raised when a tool path escapes the configured workspace."""


def workspace_root(cwd: str | os.PathLike[str]) -> Path:
    return Path(expand_path(str(cwd or "."))).resolve(strict=False)


def resolve_workspace_path(cwd: str | os.PathLike[str], path: str) -> str:
    """Resolve a user path and require it to stay inside cwd."""
    root = workspace_root(cwd)
    raw_path = str(path or "").strip()
    if not raw_path:
        raise WorkspaceAccessError("path is required")

    expanded = expand_path(raw_path)
    candidate = Path(expanded)
    if not candidate.is_absolute():
        candidate = root / expanded

    resolved = candidate.resolve(strict=False)
    if not is_within_workspace(root, resolved):
        raise WorkspaceAccessError(ACCESS_DENIED_MESSAGE)
    return str(resolved)


def is_within_workspace(cwd: str | os.PathLike[str], path: str | os.PathLike[str]) -> bool:
    root = workspace_root(cwd)
    target = Path(path).resolve(strict=False)
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def validate_shell_command_paths(cwd: str | os.PathLike[str], command: str) -> None:
    """Reject obvious shell path escapes before running inside the workspace.

    This is intentionally conservative: if a command references parent dirs,
    home dirs, or absolute paths outside the workspace, the agent should use a
    workspace-local file path instead.
    """
    command_text = str(command or "")
    command_without_urls = _URL_RE.sub("", command_text)
    try:
        tokens = shlex.split(command_without_urls, posix=os.name != "nt")
    except ValueError:
        tokens = command_without_urls.split()

    for token in tokens:
        if _contains_parent_reference(token):
            raise WorkspaceAccessError(ACCESS_DENIED_MESSAGE)
        if "$HOME" in token or "${HOME}" in token:
            raise WorkspaceAccessError(ACCESS_DENIED_MESSAGE)

        candidates: list[str] = []
        if token.startswith(("~", "/")):
            candidates.append(token)
        candidates.extend(match.group(0) for match in _ABS_OR_HOME_PATH_RE.finditer(token))

        seen: set[str] = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            resolve_workspace_path(cwd, candidate)


def _contains_parent_reference(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return (
        normalized == ".."
        or normalized.startswith("../")
        or "/../" in normalized
        or normalized.endswith("/..")
    )
