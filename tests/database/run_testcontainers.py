"""Run all database modules in one temporary PostgreSQL container."""

import argparse
import os
from pathlib import Path
import sys

from testcontainers.community.postgres import PostgresContainer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", choices=["1", "2", "3", "4"])
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    sys.path[:0] = [str(root / "backend"), str(root)]
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    os.environ["DJANGO_DEBUG"] = "1"

    import django
    from django.conf import settings
    from django.db import connections
    from django.test.utils import get_runner

    with PostgresContainer(
        "postgres:16.15-alpine",
        username="dbtest",
        password="local-db-tests-only",
        dbname="living_documents_dbtest",
        driver=None,
    ) as postgres:
        settings.DATABASES = {"default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": postgres.dbname,
            "USER": postgres.username,
            "PASSWORD": postgres.password,
            "HOST": postgres.get_container_host_ip(),
            "PORT": postgres.get_exposed_port(5432),
        }}
        django.setup()
        tags = [f"module{args.module}"] if args.module else None
        runner = get_runner(settings)(verbosity=2, interactive=False, tags=tags)
        try:
            failures = runner.run_tests(["tests.database"])
        finally:
            connections.close_all()

    print("PostgreSQL container removed.")
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
