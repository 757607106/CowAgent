from tests.conftest import (
    PLATFORM_TEST_RESET_DATABASE_ENV,
    _is_safe_platform_test_database_url,
    _platform_postgres_reset_skip_reason,
    _platform_postgres_test_database_skip_reason,
)


def test_platform_postgres_tests_refuse_live_database(monkeypatch) -> None:
    monkeypatch.setenv(
        "COW_PLATFORM_DATABASE_URL",
        "postgresql://cowplatform:secret@127.0.0.1:55432/cowplatform",
    )

    assert "Refusing to run against a live database" in _platform_postgres_test_database_skip_reason()


def test_platform_postgres_reset_requires_explicit_flag(monkeypatch) -> None:
    monkeypatch.setenv(
        "COW_PLATFORM_DATABASE_URL",
        "postgresql://cowplatform:secret@127.0.0.1:55432/cowplatform_test",
    )
    monkeypatch.delenv(PLATFORM_TEST_RESET_DATABASE_ENV, raising=False)

    assert _platform_postgres_test_database_skip_reason() == ""
    assert PLATFORM_TEST_RESET_DATABASE_ENV in _platform_postgres_reset_skip_reason()


def test_platform_postgres_reset_allows_only_test_database(monkeypatch) -> None:
    monkeypatch.setenv(PLATFORM_TEST_RESET_DATABASE_ENV, "1")

    monkeypatch.setenv(
        "COW_PLATFORM_DATABASE_URL",
        "postgresql://cowplatform:secret@127.0.0.1:55432/cowplatform",
    )
    assert "Refusing to run against a live database" in _platform_postgres_reset_skip_reason()

    monkeypatch.setenv(
        "COW_PLATFORM_DATABASE_URL",
        "postgresql://cowplatform:secret@127.0.0.1:55432/cowplatform_test",
    )
    assert _platform_postgres_reset_skip_reason() == ""
    assert _is_safe_platform_test_database_url("postgresql://u:p@127.0.0.1:5432/cowplatform_test")
