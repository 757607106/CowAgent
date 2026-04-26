from __future__ import annotations

from pathlib import Path

import pytest

from channel.web.frontend_layout import (
    FRONTEND_MODE_MODERN,
    build_frontend_layout,
    render_chat_html,
    resolve_asset_file,
    resolve_frontend_mode,
)


def _build_layout(tmp_path: Path):
    channel_file = tmp_path / "web_channel.py"
    channel_file.write_text("# stub", encoding="utf-8")
    return build_frontend_layout(channel_file)


def test_frontend_mode_always_resolves_to_modern(tmp_path: Path) -> None:
    layout = _build_layout(tmp_path)
    assert resolve_frontend_mode(layout, "unknown") == FRONTEND_MODE_MODERN
    assert resolve_frontend_mode(layout, None) == FRONTEND_MODE_MODERN


def test_frontend_layout_uses_grouped_frontend_roots(tmp_path: Path) -> None:
    layout = _build_layout(tmp_path)
    assert layout.frontend_root == tmp_path / "frontend"
    assert layout.modern_root == tmp_path / "frontend" / "modern"
    assert layout.modern_dist == tmp_path / "frontend" / "modern" / "dist"


def test_render_chat_html_reads_modern_dist_index(tmp_path: Path) -> None:
    layout = _build_layout(tmp_path)
    layout.modern_dist.mkdir(parents=True, exist_ok=True)
    (layout.modern_dist / "index.html").write_text("<html>modern</html>", encoding="utf-8")

    html = render_chat_html(layout, FRONTEND_MODE_MODERN)
    assert html == "<html>modern</html>"


def test_render_chat_html_raises_when_dist_missing(tmp_path: Path) -> None:
    layout = _build_layout(tmp_path)
    with pytest.raises(FileNotFoundError):
        render_chat_html(layout, FRONTEND_MODE_MODERN)


def test_resolve_asset_file_blocks_path_traversal(tmp_path: Path) -> None:
    layout = _build_layout(tmp_path)
    layout.modern_dist.mkdir(parents=True, exist_ok=True)
    (layout.modern_dist / "assets" / "main.js").parent.mkdir(parents=True, exist_ok=True)
    (layout.modern_dist / "assets" / "main.js").write_text("console.log('modern')", encoding="utf-8")

    assert resolve_asset_file(layout, FRONTEND_MODE_MODERN, "../web_channel.py") is None


def test_modern_asset_resolution_reads_dist_only(tmp_path: Path) -> None:
    layout = _build_layout(tmp_path)
    layout.modern_dist.mkdir(parents=True, exist_ok=True)
    asset = layout.modern_dist / "assets" / "main.js"
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_text("console.log('modern')", encoding="utf-8")

    assert resolve_asset_file(layout, FRONTEND_MODE_MODERN, "assets/main.js") == asset


def test_modern_asset_resolution_supports_assets_route_filename(tmp_path: Path) -> None:
    layout = _build_layout(tmp_path)
    layout.modern_dist.mkdir(parents=True, exist_ok=True)
    asset = layout.modern_dist / "assets" / "index-abc123.js"
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_text("console.log('modern')", encoding="utf-8")

    # /assets/(.*) route passes "index-abc123.js" (without "assets/" prefix)
    assert resolve_asset_file(layout, FRONTEND_MODE_MODERN, "index-abc123.js") == asset
