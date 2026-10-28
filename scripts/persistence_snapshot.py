"""Print a stable digest of records without credentials or sessions.

Run before and after a restart using the same Django configuration.
This script is read-only and does not create, update, or delete records.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

import django
from django.conf import settings


def main():
    sys.path.insert(0, str(Path.cwd()))
    workspace_backend = Path(__file__).resolve().parents[1] / "backend"
    if workspace_backend.exists():
        sys.path.insert(0, str(workspace_backend))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    # Django models require the application registry to be initialized.
    from core.models import Document, DocumentEvent, Template, User

    rows = {
        "documents": list(Document.objects.order_by("id").values()),
        "events": list(DocumentEvent.objects.order_by("id").values()),
        "templates": list(Template.objects.order_by("id").values()),
        "users": list(
            User.objects.order_by("id").values(
                "id", "username", "role", "is_active"
            )
        ),
    }
    payload = json.dumps(
        rows, ensure_ascii=True, sort_keys=True, default=str
    ).encode()
    print(
        json.dumps(
            {
                "database": settings.DATABASES["default"]["NAME"],
                "counts": {
                    name: len(records) for name, records in rows.items()
                },
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
