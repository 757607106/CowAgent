from __future__ import annotations

from pathlib import Path

from channel.web.frontend_layout import (
    FRONTEND_MODE_LEGACY,
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


def test_modern_mode_falls_back_to_legacy_when_dist_is_missing(tmp_path: Path) -> None:
    layout = _build_layout(tmp_path)
    assert resolve_frontend_mode(layout, FRONTEND_MODE_MODERN) == FRONTEND_MODE_LEGACY


def test_auto_mode_prefers_modern_when_dist_exists(tmp_path: Path) -> None:
    layout = _build_layout(tmp_path)
    layout.modern_dist.mkdir(parents=True, exist_ok=True)
    (layout.modern_dist / "index.html").write_text("<html>modern</html>", encoding="utf-8")

    assert resolve_frontend_mode(layout, "auto") == FRONTEND_MODE_MODERN


def test_render_legacy_chat_html_injects_cache_bust(tmp_path: Path) -> None:
    layout = _build_layout(tmp_path)
    layout.legacy_html.write_text(
        '<script src="assets/js/console.js"></script>'
        '<link rel="stylesheet" href="assets/css/console.css">',
        encoding="utf-8",
    )

    html = render_chat_html(layout, FRONTEND_MODE_LEGACY, cache_bust=True)
    assert "assets/js/console.js?v=" in html
    assert "assets/css/console.css?v=" in html


def test_resolve_asset_file_blocks_path_traversal(tmp_path: Path) -> None:
    layout = _build_layout(tmp_path)
    layout.legacy_assets.mkdir(parents=True, exist_ok=True)
    (layout.legacy_assets / "favicon.ico").write_bytes(b"ico")

    assert resolve_asset_file(layout, FRONTEND_MODE_LEGACY, "../chat.html") is None


def test_modern_asset_resolution_supports_legacy_fallback(tmp_path: Path) -> None:
    layout = _build_layout(tmp_path)

    layout.modern_dist.mkdir(parents=True, exist_ok=True)
    (layout.modern_dist / "index.html").write_text("<html>modern</html>", encoding="utf-8")
    modern_asset = layout.modern_dist / "assets" / "main.js"
    modern_asset.parent.mkdir(parents=True, exist_ok=True)
    modern_asset.write_text("console.log('modern')", encoding="utf-8")

    legacy_asset = layout.legacy_assets / "js" / "console.js"
    legacy_asset.parent.mkdir(parents=True, exist_ok=True)
    legacy_asset.write_text("console.log('legacy')", encoding="utf-8")

    assert resolve_asset_file(layout, FRONTEND_MODE_MODERN, "assets/main.js") == modern_asset
    assert resolve_asset_file(layout, FRONTEND_MODE_MODERN, "js/console.js") == legacy_asset
