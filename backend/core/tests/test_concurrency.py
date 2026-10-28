from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from ..models import Template
from ..services import Conflict, create_document, edit_document


@skipUnless(
    connection.vendor == "postgresql", "Real row-lock race requires PostgreSQL"
)
class PostgreSQLConcurrencyTests(TransactionTestCase):
    def test_two_writers_same_version_only_one_commits(self):
        user = get_user_model().objects.create_user("race-author")
        template = Template.objects.create(
            name="Race",
            schema=[
                {"name": "x", "label": "X", "type": "text", "required": True}
            ],
        )
        document = create_document(user, "Race", template, {"x": "original"})
        barrier = Barrier(2)

        def writer(title):
            close_old_connections()
            try:
                actor = get_user_model().objects.get(pk=user.pk)
                barrier.wait(timeout=10)
                try:
                    edit_document(actor, document.pk, 1, title=title)
                    return "ok"
                except Conflict:
                    return "conflict"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(writer, ["First", "Second"]))
        self.assertCountEqual(outcomes, ["ok", "conflict"])
        document.refresh_from_db()
        self.assertEqual(document.version, 2)
        self.assertEqual(document.events.count(), 2)
