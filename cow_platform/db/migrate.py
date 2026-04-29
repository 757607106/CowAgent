from __future__ import annotations

from cow_platform.db.postgres import get_database_url, run_migrations


def main() -> None:
    applied = run_migrations()
    if applied:
        print(f"PostgreSQL schema migrated: {get_database_url()} ({', '.join(applied)})")
        return
    print(f"PostgreSQL schema is ready: {get_database_url()}")


if __name__ == "__main__":
    main()
