"""Start a disposable PostgreSQL database and run plain SQL tests."""

import os
from pathlib import Path

import pytest
from psycopg.conninfo import make_conninfo
from testcontainers.community.postgres import PostgresContainer


def main():
    folder = Path(__file__).resolve().parent
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    with PostgresContainer(
        "postgres:16.15-alpine", username="dbtest",
        password="local-db-tests-only", dbname="simple_db_tests", driver=None,
    ) as postgres:
        os.environ["DB_TEST_DSN"] = make_conninfo(
            host=postgres.get_container_host_ip(),
            port=postgres.get_exposed_port(5432),
            dbname=postgres.dbname, user=postgres.username,
            password=postgres.password,
        )
        try:
            result = pytest.main([
                str(folder / "test_database.py"), "-v", "-s",
                "--tb=short", "-p", "no:cacheprovider",
            ])
        finally:
            os.environ.pop("DB_TEST_DSN", None)
    print("PostgreSQL container removed.")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
