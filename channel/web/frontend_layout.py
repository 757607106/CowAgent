from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

FRONTEND_MODE_MODERN = "modern"
FRONTEND_MODE_LEGACY = "legacy"
FRONTEND_MODE_AUTO = "auto"
_VALID_MODES = {
    FRONTEND_MODE_LEGACY,
    FRONTEND_MODE_MODERN,
    FRONTEND_MODE_AUTO,
}


@dataclass(frozen=True)
class FrontendLayout:
    web_root: Path
    frontend_root: Path
    legacy_root: Path
    modern_root: Path
    modern_dist: Path


def build_frontend_layout(web_channel_file: str | Path) -> FrontendLayout:
    web_root = Path(web_channel_file).resolve().parent
    frontend_root = web_root / "frontend"
    modern_root = frontend_root / "modern"
    return FrontendLayout(
        web_root=web_root,
        frontend_root=frontend_root,
        legacy_root=frontend_root / "legacy",
        modern_root=modern_root,
        modern_dist=modern_root / "dist",
    )


def normalize_frontend_mode(raw_mode: str | None) -> str:
    mode = str(raw_mode or FRONTEND_MODE_MODERN).strip().lower()
    if mode not in _VALID_MODES:
        return FRONTEND_MODE_MODERN
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
    return index_file.read_text(encoding="utf-8")


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
