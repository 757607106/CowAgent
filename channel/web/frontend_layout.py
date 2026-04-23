from __future__ import annotations

import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path

FRONTEND_MODE_LEGACY = "legacy"
FRONTEND_MODE_MODERN = "modern"
FRONTEND_MODE_AUTO = "auto"
_VALID_MODES = {FRONTEND_MODE_LEGACY, FRONTEND_MODE_MODERN, FRONTEND_MODE_AUTO}


@dataclass(frozen=True)
class FrontendLayout:
    web_root: Path
    legacy_html: Path
    legacy_assets: Path
    modern_dist: Path


def build_frontend_layout(web_channel_file: str | Path) -> FrontendLayout:
    web_root = Path(web_channel_file).resolve().parent
    return FrontendLayout(
        web_root=web_root,
        legacy_html=web_root / "chat.html",
        legacy_assets=web_root / "static",
        modern_dist=web_root / "ui" / "dist",
    )


def normalize_frontend_mode(raw_mode: str | None) -> str:
    mode = str(raw_mode or FRONTEND_MODE_LEGACY).strip().lower()
    if mode not in _VALID_MODES:
        return FRONTEND_MODE_LEGACY
    return mode


def resolve_frontend_mode(layout: FrontendLayout, requested_mode: str | None) -> str:
    mode = normalize_frontend_mode(requested_mode)
    modern_ready = (layout.modern_dist / "index.html").is_file()
    if mode == FRONTEND_MODE_AUTO:
        return FRONTEND_MODE_MODERN if modern_ready else FRONTEND_MODE_LEGACY
    if mode == FRONTEND_MODE_MODERN and modern_ready:
        return FRONTEND_MODE_MODERN
    return FRONTEND_MODE_LEGACY


def render_chat_html(
    layout: FrontendLayout,
    requested_mode: str | None,
    *,
    cache_bust: bool = True,
) -> str:
    mode = resolve_frontend_mode(layout, requested_mode)
    if mode == FRONTEND_MODE_MODERN:
        return layout.modern_dist.joinpath("index.html").read_text(encoding="utf-8")

    html = layout.legacy_html.read_text(encoding="utf-8")
    if cache_bust:
        token = str(int(time.time()))
        html = html.replace("assets/js/console.js", f"assets/js/console.js?v={token}")
        html = html.replace("assets/css/console.css", f"assets/css/console.css?v={token}")
    return html


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
    normalized = str(file_path or "").lstrip("/").strip()
    if not normalized:
        return None

    mode = resolve_frontend_mode(layout, requested_mode)
    base_dirs = [layout.legacy_assets, layout.modern_dist]
    if mode == FRONTEND_MODE_MODERN:
        base_dirs = [layout.modern_dist, layout.legacy_assets]

    for base_dir in base_dirs:
        candidate = _safe_resolve(base_dir, normalized)
        if candidate is not None and candidate.is_file():
            return candidate
    return None


def guess_content_type(path: Path) -> str:
    return mimetypes.guess_type(str(path))[0] or "application/octet-stream"
