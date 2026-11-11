"""Real PostgreSQL checks. SQL fixtures are shared with the report."""

from io import BytesIO
from pathlib import Path

from django.contrib.auth import authenticate
from django.db import DataError, IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, tag
from docx import Document as WordDocument
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from core.models import Document, DocumentEvent, Template, User
from core.services import create_document, edit_document, transition_document
from core.views import AnalyticsView, DocumentViewSet


class DatabaseFixture(TestCase):
    @classmethod
    def setUpTestData(cls):
        if connection.vendor != "postgresql":
            raise RuntimeError("These tests require PostgreSQL.")
        with connection.cursor() as cursor:
            cursor.execute(
                (Path(__file__).parent / "02_seed.sql").read_text("utf-8")
            )
        cls.author = User.objects.get(pk=101)
        cls.other = User.objects.get(pk=102)
        cls.manager = User.objects.get(pk=103)
        cls.template = Template.objects.get(pk=201)

    def sql(self, statement, params=()):
        with connection.cursor() as cursor:
            cursor.execute(statement, params)
            return cursor.fetchall() if cursor.description else []

    def reject(self, exception, statement, params=()):
        with self.assertRaises(exception):
            with transaction.atomic():
                self.sql(statement, params)
                self.sql("SET CONSTRAINTS ALL IMMEDIATE")

    def analytics(self, user):
        request = APIRequestFactory().get("/api/analytics/")
        force_authenticate(request, user)
        return AnalyticsView.as_view()(request).data


@tag("database", "module1")
class Module1DatabaseTests(DatabaseFixture):
    def test_unique_username_and_field_length(self):
        self.reject(
            IntegrityError,
            "UPDATE core_user SET username='db_author' WHERE id=102",
        )
        self.reject(
            DataError, "UPDATE core_user SET role=%s WHERE id=101", ["x" * 11]
        )

    def test_persisted_password_and_inactive_login(self):
        self.assertTrue(self.author.check_password("Database-test-491!"))
        self.assertNotEqual(self.author.password, "Database-test-491!")
        self.assertEqual(
            authenticate(username="db_author", password="Database-test-491!"),
            self.author,
        )
        self.author.is_active = False
        self.author.save()
        self.assertIsNone(
            authenticate(username="db_author", password="Database-test-491!")
        )

    def test_role_scope_is_applied_to_database_queries(self):
        self.assertEqual(self.analytics(self.author)["total"], 1)
        self.assertEqual(self.analytics(self.other)["total"], 1)
        self.assertEqual(self.analytics(self.manager)["total"], 2)
        self.assertEqual(self.analytics(User.objects.get(pk=104))["total"], 2)

    def test_owner_and_actor_foreign_keys_restrict_deletion(self):
        self.reject(IntegrityError, "DELETE FROM core_user WHERE id=101")
        self.reject(IntegrityError, "DELETE FROM core_user WHERE id=103")
        with self.assertRaises(ProtectedError):
            self.author.delete()


@tag("database", "module2")
class Module2DatabaseTests(DatabaseFixture):
    def test_template_unique_name_and_document_required_title(self):
        self.reject(
            IntegrityError,
            "UPDATE core_template SET name='DB report' WHERE id=202",
        )
        self.reject(
            IntegrityError, "UPDATE core_document SET title=NULL WHERE id=301"
        )
        self.reject(
            DataError, "UPDATE core_document SET title=%s WHERE id=301",
            ["x" * 251],
        )

    def test_jsonb_type_and_unicode_roundtrip(self):
        self.assertEqual(
            self.sql("SELECT pg_typeof(data)::text FROM core_document LIMIT 1"),
            [("jsonb",)],
        )
        self.assertEqual(Document.objects.get(pk=301).data["text"], "Звіт")
        self.reject(
            DataError, "UPDATE core_document SET data=%s::jsonb WHERE id=301",
            ["{invalid"],
        )

    def test_template_foreign_key_and_protection(self):
        self.reject(
            IntegrityError,
            "UPDATE core_document SET template_id=99999 WHERE id=301",
        )
        with self.assertRaises(ProtectedError):
            self.template.delete()

    def test_invalid_fields_create_neither_document_nor_event(self):
        before = (Document.objects.count(), DocumentEvent.objects.count())
        with self.assertRaises(ValidationError):
            create_document(self.author, "Invalid", self.template, {})
        self.assertEqual(
            (Document.objects.count(), DocumentEvent.objects.count()), before
        )

    def test_snapshot_survives_template_update(self):
        document = create_document(
            self.author, "Snapshot", self.template, {"text": "Дані"}
        )
        self.template.name = "Changed"
        self.template.schema = []
        self.template.save()
        document.refresh_from_db()
        self.assertEqual(document.template_snapshot["name"], "DB report")
        self.assertEqual(document.template_snapshot["schema"][0]["name"], "text")


@tag("database", "module3")
class Module3DatabaseTests(DatabaseFixture):
    def test_master_detail_chain_and_orphan_rejection(self):
        rows = self.sql(
            "SELECT u.id,d.id,e.id FROM core_user u "
            "JOIN core_document d ON d.owner_id=u.id "
            "JOIN core_documentevent e ON e.document_id=d.id "
            "WHERE d.id=301 ORDER BY e.created_at,e.id"
        )
        self.assertEqual(rows, [(101, 301, 401)])
        self.reject(
            IntegrityError,
            "UPDATE core_documentevent SET document_id=99999 WHERE id=401",
        )

    def test_complete_cycle_persists_history_and_final_state(self):
        doc = transition_document(self.author, 301, 1, "submit")
        doc = transition_document(self.manager, 301, doc.version, "approve")
        doc = transition_document(self.author, 301, doc.version, "complete")
        doc.refresh_from_db()
        self.assertEqual(doc.status, "completed")
        self.assertEqual(doc.version, 4)
        self.assertIsNotNone(doc.completed_at)
        self.assertEqual(
            list(doc.events.values_list("to_status", flat=True)),
            ["draft", "submitted", "approved", "completed"],
        )
        with self.assertRaises(ValidationError):
            edit_document(self.author, doc.pk, doc.version, title="Forbidden")

    def test_unauthorized_transition_does_not_change_rows(self):
        before = list(DocumentEvent.objects.values_list("id", flat=True))
        with self.assertRaises(PermissionDenied):
            transition_document(self.other, 301, 1, "submit")
        self.assertEqual(Document.objects.get(pk=301).status, "draft")
        self.assertEqual(
            list(DocumentEvent.objects.values_list("id", flat=True)), before
        )

    def test_real_database_constraint_failure_rolls_back_transition(self):
        # A transient CHECK forces the actual event INSERT to fail.
        with transaction.atomic():
            self.sql("SET CONSTRAINTS ALL IMMEDIATE")
            self.sql(
                "ALTER TABLE core_documentevent ADD CONSTRAINT test_no_submit "
                "CHECK (document_id <> 301 OR to_status <> 'submitted')"
            )
            with self.assertRaises(IntegrityError):
                transition_document(self.author, 301, 1, "submit")
            self.sql(
                "ALTER TABLE core_documentevent DROP CONSTRAINT test_no_submit"
            )
        doc = Document.objects.get(pk=301)
        self.assertEqual((doc.status, doc.version), ("draft", 1))
        self.assertEqual(doc.events.count(), 1)

    def test_version_check_constraint_and_orm_cascade(self):
        self.reject(
            IntegrityError, "UPDATE core_document SET version=-1 WHERE id=301"
        )
        Document.objects.get(pk=301).delete()
        self.assertFalse(DocumentEvent.objects.filter(document_id=301).exists())
        self.assertTrue(User.objects.filter(pk=101).exists())


@tag("database", "module4")
class Module4DatabaseTests(DatabaseFixture):
    def test_sql_aggregates_match_dashboard(self):
        stats = self.analytics(self.manager)
        rows = self.sql(
            "SELECT status,COUNT(*) FROM core_document GROUP BY status"
        )
        for status, count in rows:
            self.assertEqual(stats["by_status"][status], count)
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["average_cycle_seconds"], 7200)

    def test_dashboard_reflects_persisted_service_changes(self):
        self.assertEqual(self.analytics(self.author)["pending_approval"], 0)
        transition_document(self.author, 301, 1, "submit")
        self.assertEqual(self.analytics(self.author)["pending_approval"], 1)

    def test_docx_reads_persisted_snapshot_without_database_writes(self):
        before = self.sql("SELECT * FROM core_document ORDER BY id")
        events = self.sql("SELECT * FROM core_documentevent ORDER BY id")
        request = APIRequestFactory().get("/api/documents/301/export/")
        force_authenticate(request, self.author)
        response = DocumentViewSet.as_view({"get": "export"})(request, pk=301)
        self.assertEqual(response.status_code, 200)
        # Close the stream without sending request_finished, which would
        # close the shared connection inside Django's TestCase transaction.
        self.addCleanup(response.file_to_stream.close)
        word = WordDocument(BytesIO(b"".join(response.streaming_content)))
        self.assertEqual(word.paragraphs[0].text, "DB draft")
        self.assertIn("Звіт", "\n".join(p.text for p in word.paragraphs))
        self.assertEqual(self.sql("SELECT * FROM core_document ORDER BY id"), before)
        self.assertEqual(
            self.sql("SELECT * FROM core_documentevent ORDER BY id"), events
        )

    def test_indexes_and_foreign_key_triggers_are_present(self):
        indexes = self.sql(
            "SELECT indexdef FROM pg_indexes WHERE tablename='core_document'"
        )
        self.assertTrue(any("(owner_id, status)" in row[0] for row in indexes))
        self.assertTrue(any("(template_id, created_at)" in row[0] for row in indexes))
        triggers = self.sql(
            "SELECT count(*) FROM pg_trigger WHERE tgisinternal "
            "AND tgrelid='core_documentevent'::regclass"
        )[0][0]
        self.assertGreater(triggers, 0)


@tag("database")
class DatabaseInventoryTests(DatabaseFixture):
    def test_direct_sql_bypasses_application_choices(self):
        # Characterization: document the current DB protection boundary.
        self.sql("UPDATE core_user SET role='unknown' WHERE id=101")
        self.sql("UPDATE core_document SET status='unknown' WHERE id=301")
        self.assertEqual(User.objects.get(pk=101).role, "unknown")
        self.assertEqual(Document.objects.get(pk=301).status, "unknown")

    def test_application_routines_and_custom_triggers_inventory(self):
        self.assertEqual(
            self.sql(
                "SELECT count(*) FROM pg_trigger "
                "WHERE NOT tgisinternal AND tgrelid IN "
                "('core_document'::regclass,'core_documentevent'::regclass,"
                "'core_user'::regclass,'core_template'::regclass)"
            ), [(0,)],
        )
        self.assertEqual(
            self.sql(
                "SELECT count(*) FROM pg_proc p JOIN pg_namespace n "
                "ON n.oid=p.pronamespace WHERE n.nspname='public' "
                "AND p.prokind IN ('f','p')"
            ), [(0,)],
        )
