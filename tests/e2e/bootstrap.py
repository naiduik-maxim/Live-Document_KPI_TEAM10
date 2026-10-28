"""Create synthetic identities only in the isolated E2E database."""

import os
import sys
from pathlib import Path

import django
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command


def main():
    if os.environ.get("E2E_TEST_DATABASE") != "living_documents_e2e":
        raise SystemExit(
            "Refusing synthetic credentials without "
            "E2E_TEST_DATABASE=living_documents_e2e"
        )
    sys.path.insert(
        0,
        (
            "/app"
            if Path("/app/manage.py").exists()
            else str(Path(__file__).resolve().parents[2] / "backend")
        ),
    )
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    if settings.DATABASES["default"]["NAME"] != "living_documents_e2e":
        raise SystemExit("Refusing to seed non-E2E database")
    for username, role in [
        ("e2e_teacher", "teacher"),
        ("e2e_manager", "manager"),
        ("e2e_admin", "admin"),
    ]:
        user, _ = get_user_model().objects.get_or_create(username=username)
        user.role = role
        user.is_active = True
        user.set_password("Synthetic-E2E-Password-491!")
        user.save()
    call_command("seed_templates")
    print("Synthetic E2E users and templates ready.")


if __name__ == "__main__":
    main()
