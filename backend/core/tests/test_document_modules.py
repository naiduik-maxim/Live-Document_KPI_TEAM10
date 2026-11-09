from datetime import UTC, datetime, timedelta
from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, tag
from docx import Document as WordDocument
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from ..models import Document, Template, User
from ..services import create_document, transition_document
from ..validation import validate_data
from ..views import AnalyticsView, DocumentViewSet, LoginView


@tag("module1")
class LoginTests(SimpleTestCase):
    def setUp(self):
        self.request = APIRequestFactory().post(
            "/api/auth/login/",
            {"username": "lecturer", "password": "test-only"},
            format="json",
        )

    @patch("core.views.login", autospec=True)
    @patch("core.views.authenticate", autospec=True)
    def test_session_uses_authenticated_user_and_effective_role(
        self, authenticate, login
    ):
        user = User(username="lecturer", role="teacher", is_superuser=True)
        authenticate.return_value = user
        response = LoginView.as_view()(self.request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], "admin")
        self.assertNotIn("password", response.data)
        request = authenticate.call_args.args[0]
        authenticate.assert_called_once_with(
            request, username="lecturer", password="test-only"
        )
        login.assert_called_once_with(request, user)

    @patch("core.views.login", autospec=True)
    @patch("core.views.authenticate", return_value=None)
    def test_invalid_credentials_do_not_start_session(
        self, authenticate, login
    ):
        response = LoginView.as_view()(self.request)
        self.assertEqual(response.status_code, 401)
        authenticate.assert_called_once()
        login.assert_not_called()


@tag("module2")
class TemplateValidationTests(SimpleTestCase):
    def test_selected_schema_reports_all_invalid_fields_together(self):
        schema = [
            {"name": "topic", "type": "text", "required": True},
            {"name": "date", "type": "date"},
            {"name": "count", "type": "number", "min": 0},
        ]
        with self.assertRaises(ValidationError) as error:
            validate_data({"date": "2026-02-29", "count": -1}, schema)
        self.assertSetEqual(
            set(error.exception.detail["data"]), {"topic", "date", "count"}
        )
        valid = {"topic": "Звіт", "date": "2028-02-29", "count": 0}
        self.assertEqual(validate_data(valid, schema), valid)


@tag("module3")
class DocumentAgeTests(SimpleTestCase):
    def test_clock_advances_only_until_completion(self):
        start = datetime(2026, 1, 1, tzinfo=UTC)
        document = Document(created_at=start)
        with patch("core.models.timezone.now") as clock:
            clock.return_value = start + timedelta(minutes=20)
            self.assertEqual(document.age_seconds, 1200)
            clock.return_value += timedelta(minutes=5)
            self.assertEqual(document.age_seconds, 1500)
            document.completed_at = clock.return_value
            clock.return_value += timedelta(days=1)
            self.assertEqual(document.age_seconds, 1500)


@tag("module4")
class ExportTests(SimpleTestCase):
    def test_download_reopens_with_snapshot_content_and_formatting(self):
        document = Document(
            pk=42,
            title="Звіт кафедри",
            data={"count": 0, "body": "Вступ\n- Висновок"},
            template_snapshot={
                "name": "Звіт",
                "description": "Бланк",
                "schema": [
                    {"name": "count", "label": "Кількість", "type": "number"},
                    {"name": "body", "label": "Текст", "type": "textarea"},
                ],
            },
        )
        view = DocumentViewSet()
        with patch.object(view, "get_object", return_value=document):
            response = view.export(None)
        self.addCleanup(response.close)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("42.docx", response["Content-Disposition"])
        word = WordDocument(BytesIO(b"".join(response.streaming_content)))
        self.assertEqual(word.paragraphs[0].text, "Звіт кафедри")
        self.assertEqual(word.paragraphs[0].style.name, "Title")
        self.assertEqual(
            [(p.text, p.style.name) for p in word.paragraphs[-3:]],
            [
                ("Текст", "Heading 1"),
                ("Вступ", "Normal"),
                ("Висновок", "List Bullet"),
            ],
        )
        table = word.tables[0]
        self.assertEqual(table.style.name, "Table Grid")
        self.assertEqual(
            [c.text for c in table.rows[0].cells], ["Кількість", "0"]
        )
        self.assertEqual(word.styles["Normal"].font.name, "Times New Roman")
        self.assertEqual(word.styles["Normal"].font.size.pt, 12)
        self.assertAlmostEqual(word.sections[0].page_width.cm, 21, places=2)
        self.assertAlmostEqual(word.sections[0].page_height.cm, 29.7, places=2)


@tag("module4")
class DashboardLifecycleTests(TestCase):
    def test_counts_follow_persisted_transitions_and_role_scope(self):
        owner = User.objects.create(username="teacher")
        manager = User.objects.create(username="manager", role="manager")
        template = Template.objects.create(name="Звіт")
        document = create_document(owner, "Мій звіт", template, {})
        create_document(manager, "Інший звіт", template, {})

        def dashboard(user):
            request = APIRequestFactory().get("/api/analytics/")
            force_authenticate(request, user=user)
            return AnalyticsView.as_view()(request).data

        original = dashboard(owner)
        self.assertEqual(original["total"], 1)
        self.assertEqual(original["by_status"]["draft"], 1)
        self.assertIsNone(original["average_cycle_seconds"])
        self.assertEqual(dashboard(manager)["total"], 2)
        transition_document(owner, document.pk, 1, "submit")
        self.assertEqual(dashboard(owner)["pending_approval"], 1)
        transition_document(manager, document.pk, 2, "approve")
        document = transition_document(owner, document.pk, 3, "complete")
        final = dashboard(owner)
        self.assertEqual(final["pending_approval"], 0)
        self.assertEqual(final["by_status"]["completed"], 1)
        self.assertEqual(final["completed_in_period"], 1)
        self.assertAlmostEqual(
            final["average_cycle_seconds"], document.age_seconds, places=5
        )
        self.assertEqual(
            list(document.events.values_list("from_status", "to_status")),
            [
                ("", "draft"),
                ("draft", "submitted"),
                ("submitted", "approved"),
                ("approved", "completed"),
            ],
        )
