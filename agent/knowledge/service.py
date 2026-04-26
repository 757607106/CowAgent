"""
Knowledge service for handling knowledge base operations.

Provides a unified interface for listing, reading, and graphing knowledge files,
callable from the web console, API, or CLI.

Knowledge file layout (under workspace_root):
    knowledge/index.md
    knowledge/log.md
    knowledge/<category>/<slug>.md
"""

import os
import re
from pathlib import Path
from typing import Optional

from common.log import logger
from config import conf

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+\.md)\)")


class KnowledgeService:
    """
    High-level service for knowledge base queries.
    Operates directly on the filesystem.
    """

    def __init__(self, workspace_root: str, enabled: Optional[bool] = None):
        self.workspace_root = workspace_root
        self.knowledge_dir = os.path.join(workspace_root, "knowledge")
        self.enabled = conf().get("knowledge", True) if enabled is None else bool(enabled)

    # ------------------------------------------------------------------
    # list — directory tree with stats
    # ------------------------------------------------------------------
    def list_tree(self) -> dict:
        """
        Return the knowledge directory tree grouped by category.

        Returns::

            {
                "tree": [
                    {
                        "dir": "concepts",
                        "files": [
                            {"name": "moe.md", "title": "MoE", "size": 1234},
                            ...
                        ]
                    },
                    ...
                ],
                "stats": {"pages": 15, "size": 32768},
                "enabled": true
            }
        """
        if not self.enabled:
            return {"tree": [], "stats": {"pages": 0, "size": 0}, "enabled": False}

        if not os.path.isdir(self.knowledge_dir):
            return {"tree": [], "stats": {"pages": 0, "size": 0}, "enabled": self.enabled}

        tree = []
        total_files = 0
        total_bytes = 0
        for name in sorted(os.listdir(self.knowledge_dir)):
            full = os.path.join(self.knowledge_dir, name)
            if not os.path.isdir(full) or name.startswith("."):
                continue
            files = []
            for fname in sorted(os.listdir(full)):
                if fname.endswith(".md") and not fname.startswith("."):
                    fpath = os.path.join(full, fname)
                    size = os.path.getsize(fpath)
                    total_files += 1
                    total_bytes += size
                    title = fname.replace(".md", "")
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            first_line = f.readline().strip()
                        title = self._extract_markdown_title(first_line, title)
                    except Exception:
                        pass
                    files.append({"name": fname, "title": title, "size": size})
            tree.append({"dir": name, "files": files})

        return {
            "tree": tree,
            "stats": {"pages": total_files, "size": total_bytes},
            "enabled": self.enabled,
        }

    # ------------------------------------------------------------------
    # read — single file content
    # ------------------------------------------------------------------
    def read_file(self, rel_path: str) -> dict:
        """
        Read a single knowledge markdown file.

        :param rel_path: Relative path within knowledge/, e.g. ``concepts/moe.md``
        :return: dict with ``content`` and ``path``
        :raises ValueError: if path is invalid or escapes knowledge dir
        :raises FileNotFoundError: if file does not exist
        """
        if not self.enabled:
            raise RuntimeError("knowledge is disabled for this agent")

        if not rel_path or ".." in rel_path:
            raise ValueError("invalid path")

        full_path = os.path.normpath(os.path.join(self.knowledge_dir, rel_path))
        allowed = os.path.normpath(self.knowledge_dir)
        if not full_path.startswith(allowed + os.sep) and full_path != allowed:
            raise ValueError("path outside knowledge dir")

        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"file not found: {rel_path}")

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content, "path": rel_path}

    # ------------------------------------------------------------------
    # graph — nodes and links for visualization
    # ------------------------------------------------------------------
    def build_graph(self) -> dict:
        """
        Parse all knowledge pages and extract real cross-reference links.

        Returns::

            {
                "nodes": [
                    {"id": "concepts/moe.md", "label": "MoE", "category": "concepts"},
                    ...
                ],
                "links": [
                    {"source": "concepts/moe.md", "target": "entities/deepseek.md"},
                    ...
                ]
            }
        """
        if not self.enabled:
            return {"nodes": [], "links": [], "enabled": False}

        knowledge_path = Path(self.knowledge_dir)
        if not knowledge_path.is_dir():
            return {"nodes": [], "links": [], "enabled": self.enabled}

        nodes = {}
        links = []
        for md_file in sorted(knowledge_path.rglob("*.md")):
            rel = str(md_file.relative_to(knowledge_path))
            if rel in ("index.md", "log.md"):
                continue

            parts = rel.split("/")
            category = parts[0] if len(parts) > 1 else "root"
            title = md_file.stem.replace("-", " ").title()
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                content = ""

            title = self._extract_markdown_title(content, title)
            for _, link_target in MARKDOWN_LINK_RE.findall(content):
                resolved = (md_file.parent / link_target).resolve()
                try:
                    target_rel = str(resolved.relative_to(knowledge_path))
                except ValueError:
                    continue
                if target_rel != rel:
                    links.append({"source": rel, "target": target_rel})
            nodes[rel] = {"id": rel, "label": title, "category": category}

        valid_ids = set(nodes.keys())
        links = [link for link in links if link["source"] in valid_ids and link["target"] in valid_ids]
        seen = set()
        deduped = []
        for link in links:
            key = tuple(sorted([link["source"], link["target"]]))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(link)

        return {"nodes": list(nodes.values()), "links": deduped, "enabled": self.enabled}

    @staticmethod
    def _extract_markdown_title(content: str, default_title: str) -> str:
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("# "):
                return stripped[2:].strip() or default_title
            return default_title
        return default_title

    # ------------------------------------------------------------------
    # dispatch — single entry point for protocol messages
    # ------------------------------------------------------------------
    def dispatch(self, action: str, payload: Optional[dict] = None) -> dict:
        """
        Dispatch a knowledge management action.

        :param action: ``list``, ``read``, or ``graph``
        :param payload: action-specific payload
        :return: protocol-compatible response dict
        """
        payload = payload or {}
        try:
            if action == "list":
                result = self.list_tree()
                return {"action": action, "code": 200, "message": "success", "payload": result}

            elif action == "read":
                path = payload.get("path")
                if not path:
                    return {"action": action, "code": 400, "message": "path is required", "payload": None}
                result = self.read_file(path)
                return {"action": action, "code": 200, "message": "success", "payload": result}

            elif action == "graph":
                result = self.build_graph()
                return {"action": action, "code": 200, "message": "success", "payload": result}

            else:
                return {"action": action, "code": 400, "message": f"unknown action: {action}", "payload": None}

        except (ValueError, RuntimeError) as e:
            return {"action": action, "code": 403, "message": str(e), "payload": None}
        except FileNotFoundError as e:
            return {"action": action, "code": 404, "message": str(e), "payload": None}
        except Exception as e:
            logger.error(f"[KnowledgeService] dispatch error: action={action}, error={e}")
            return {"action": action, "code": 500, "message": str(e), "payload": None}
