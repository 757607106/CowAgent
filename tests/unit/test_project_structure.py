from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_platform_docs_are_grouped_under_platform_design() -> None:
    assert not (REPO_ROOT / "docs" / "add pr").exists()
    assert (REPO_ROOT / "docs" / "platform" / "design").is_dir()


def test_web_frontend_uses_modern_runtime_without_legacy_static_ui() -> None:
    web_root = REPO_ROOT / "channel" / "web"
    assert (web_root / "frontend" / "modern" / "src").is_dir()
    assert (web_root / "frontend" / "modern" / "package.json").is_file()
    assert not (web_root / "frontend" / "legacy").exists()
    assert not (web_root / "ui").exists()
    assert not (web_root / "chat.html").exists()
    assert not (web_root / "static").exists()


def test_web_backend_handlers_are_split_by_responsibility() -> None:
    web_root = REPO_ROOT / "channel" / "web"
    for module_name in [
        "core.py",
        "configuration.py",
        "channel_admin.py",
        "platform.py",
        "callbacks.py",
        "workspace.py",
        "dependencies.py",
    ]:
        assert (web_root / "handlers" / module_name).is_file()

    with (web_root / "web_channel.py").open(encoding="utf-8") as f:
        assert sum(1 for _ in f) < 1500


def test_platform_scripts_are_grouped_with_root_wrappers() -> None:
    platform_dir = REPO_ROOT / "scripts" / "platform"
    for script_name in [
        "platform_real_scenario_test.py",
        "web_console_platform_bridge_test.py",
        "run_real_integration_matrix.py",
    ]:
        assert (platform_dir / script_name).is_file()
        assert (REPO_ROOT / "scripts" / script_name).is_file()


def test_shared_test_fakes_live_under_support_package() -> None:
    assert (REPO_ROOT / "tests" / "support" / "platform_fakes.py").is_file()
    assert not (REPO_ROOT / "tests" / "platform_fakes.py").exists()


def test_tests_root_does_not_contain_direct_test_modules() -> None:
    root_tests = sorted(path.name for path in (REPO_ROOT / "tests").glob("test_*.py"))
    assert root_tests == []
