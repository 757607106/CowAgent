from __future__ import annotations

from cow_platform.db.postgres import ensure_database, get_database_url


def main() -> None:
    ensure_database()
    print(f"PostgreSQL schema is ready: {get_database_url()}")


if __name__ == "__main__":
    main()
