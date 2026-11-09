"""Independent HTTP-level concurrency acceptance test on PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.db import close_old_connections, connection
from django.test import TransactionTestCase, tag
from rest_framework.test import APIClient

from core.models import Document, DocumentEvent, Template, User


@tag("module3")
@skipUnless(
    connection.vendor == "postgresql", "PostgreSQL row locking required"
)
class PostgreSQLAPIRaceTests(TransactionTestCase):
    def test_concurrent_http_edits_commit_one_event_and_reject_stale_version(
        self,
    ):
        user = User.objects.create_user("qa_race")
        template = Template.objects.create(name="QA race", schema=[])
        client = APIClient()
        client.force_authenticate(user)
        created = client.post(
            "/api/documents/",
            {"title": "Original", "template": template.pk, "data": {}},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        doc_id, version = created.data["id"], created.data["version"]
        events_before = DocumentEvent.objects.filter(
            document_id=doc_id
        ).count()
        barrier = Barrier(2)

        def edit(title):
            close_old_connections()
            try:
                local_client = APIClient()
                local_client.force_authenticate(User.objects.get(pk=user.pk))
                barrier.wait(timeout=10)
                response = local_client.patch(
                    f"/api/documents/{doc_id}/",
                    {"title": title, "version": version},
                    format="json",
                )
                return response.status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(edit, ["First writer", "Second writer"]))
        self.assertEqual(sorted(results), [200, 409])
        doc = Document.objects.get(pk=doc_id)
        self.assertEqual(doc.version, version + 1)
        self.assertIn(doc.title, ["First writer", "Second writer"])
        self.assertEqual(
            DocumentEvent.objects.filter(document_id=doc_id).count(),
            events_before + 1,
        )
