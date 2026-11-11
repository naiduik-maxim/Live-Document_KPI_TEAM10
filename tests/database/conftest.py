"""Load the SQL once; roll back each test's changes."""

import os
from pathlib import Path

import psycopg
import pytest


@pytest.fixture(scope="session")
def database():
    dsn = os.environ.get("DB_TEST_DSN")
    if not dsn:
        pytest.fail("Run tests/database/run.ps1 to start Testcontainers.")
    folder = Path(__file__).parent
    with psycopg.connect(dsn) as conn:
        if conn.info.dbname != "simple_db_tests":
            pytest.fail("Only the disposable simple_db_tests database is allowed.")
        conn.execute((folder / "01_schema.sql").read_text("utf-8"))
        conn.execute("SET search_path TO public")
        conn.execute((folder / "02_seed.sql").read_text("utf-8"))
        count = conn.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE'"
        ).fetchone()[0]
        assert count == 13
    print("SQL loaded: 13 tables; seed: 2 users, 1 template, 1 document, 1 event.")
    return dsn


@pytest.fixture
def db(database):
    with psycopg.connect(database) as conn:
        try:
            conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
            yield conn
        finally:
            conn.rollback()
