"""Load the SQL once; roll back each test's changes."""

import os
from pathlib import Path

import psycopg
from psycopg import sql
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
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE'"
        ).fetchall()
        assert len(tables) == 13
        seed_rows = sum(
            conn.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(name))
            ).fetchone()[0]
            for (name,) in tables
        )
        assert seed_rows == 8
    print(f"SQL loaded: {len(tables)} tables; {seed_rows} seed rows.")
    return dsn


@pytest.fixture
def db(database):
    with psycopg.connect(database) as conn:
        try:
            conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
            yield conn
        finally:
            conn.rollback()
