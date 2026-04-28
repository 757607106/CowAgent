from __future__ import annotations

import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

FRONTEND_MODE_MODERN = "modern"


@dataclass(frozen=True)
class FrontendLayout:
    web_root: Path
    frontend_root: Path
    modern_root: Path
    modern_dist: Path


def build_frontend_layout(web_channel_file: str | Path) -> FrontendLayout:
    web_root = Path(web_channel_file).resolve().parent
    frontend_root = web_root / "frontend"
    modern_root = frontend_root / "modern"
    return FrontendLayout(
        web_root=web_root,
        frontend_root=frontend_root,
        modern_root=modern_root,
        modern_dist=modern_root / "dist",
    )


def normalize_frontend_mode(raw_mode: str | None) -> str:
    _ = raw_mode
    # 平台运行时只允许 modern 构建产物入口。
    return FRONTEND_MODE_MODERN


def resolve_frontend_mode(layout: FrontendLayout, requested_mode: str | None) -> str:
    _ = layout
    _ = requested_mode
    return FRONTEND_MODE_MODERN


def render_chat_html(
    layout: FrontendLayout,
    requested_mode: str | None,
    *,
    cache_bust: bool = True,
) -> str:
    _ = requested_mode
    _ = cache_bust
    index_file = layout.modern_dist / "index.html"
    if not index_file.is_file():
        raise FileNotFoundError(
            "Modern frontend dist not found. Expected file: "
            f"{index_file}"
        )
    html = index_file.read_text(encoding="utf-8")
    if not cache_bust:
        return html
    return _append_asset_versions(layout, html)


def _append_asset_versions(layout: FrontendLayout, html: str) -> str:
    def replace(match: re.Match[str]) -> str:
        attr = match.group("attr")
        quote = match.group("quote")
        url = match.group("url")
        parsed = urlsplit(url)
        asset = resolve_asset_file(layout, FRONTEND_MODE_MODERN, parsed.path)
        if asset is None:
            return match.group(0)
        separator = "&" if parsed.query else "?"
        return f"{attr}{quote}{url}{separator}v={asset.stat().st_mtime_ns}{quote}"

    return re.sub(
        r"(?P<attr>\b(?:src|href)=)(?P<quote>[\"'])(?P<url>/assets/[^\"']+)(?P=quote)",
        replace,
        html,
    )


def _safe_resolve(root: Path, relative_path: str) -> Path | None:
    resolved_root = root.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError:
        return None
    return candidate


def resolve_asset_file(
    layout: FrontendLayout,
    requested_mode: str | None,
    file_path: str,
) -> Path | None:
    normalized = urlsplit(str(file_path or "").strip()).path.lstrip("/").strip()
    if not normalized:
        return None

    _ = requested_mode
    # /assets/(.*) routes pass file names like "index-xxxx.js".
    # Vite emits these files under dist/assets/, so we try both locations.
    candidates = [normalized]
    if normalized.startswith("assets/"):
        candidates.append(normalized[len("assets/"):])
    else:
        candidates.append(f"assets/{normalized}")

    for relative_path in candidates:
        candidate = _safe_resolve(layout.modern_dist, relative_path)
        if candidate is not None and candidate.is_file():
            return candidate
    return None


def guess_content_type(path: Path) -> str:
    return mimetypes.guess_type(str(path))[0] or "application/octet-stream"
