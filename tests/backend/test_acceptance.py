"""Independent contract-level tests without production code changes."""

from datetime import timedelta
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Document, DocumentEvent, Template, User


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(
            "qa_teacher", password="Test-Password-491!"
        )
        cls.other = User.objects.create_user(
            "qa_other", password="Test-Password-491!"
        )
        cls.manager = User.objects.create_user(
            "qa_manager", password="Test-Password-491!", role="manager"
        )
        cls.admin = User.objects.create_user(
            "qa_admin", password="Test-Password-491!", role="admin"
        )
        cls.template = Template.objects.create(
            name="QA Заява",
            schema=[
                {
                    "name": "text",
                    "label": "Текст",
                    "type": "text",
                    "required": True,
                    "max_length": 30,
                },
                {
                    "name": "body",
                    "label": "Опис",
                    "type": "textarea",
                    "required": False,
                    "max_length": 500,
                },
                {
                    "name": "amount",
                    "label": "Кількість",
                    "type": "number",
                    "required": True,
                    "min": 1,
                    "max": 10,
                },
                {
                    "name": "date",
                    "label": "Дата",
                    "type": "date",
                    "required": True,
                },
                {
                    "name": "choice",
                    "label": "Тип",
                    "type": "select",
                    "required": True,
                    "choices": ["А", "Б"],
                },
            ],
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.teacher)

    def data(self):
        return {
            "text": "Українська заява",
            "body": "Перший абзац\n- Пункт",
            "amount": 1,
            "date": "2026-10-19",
            "choice": "А",
        }

    def create(self, **overrides):
        payload = {
            "title": "Тестова заява",
            "template": self.template.pk,
            "data": self.data(),
        }
        payload.update(overrides)
        response = self.client.post("/api/documents/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def transition(self, doc, action, user=None, comment=""):
        self.client.force_authenticate(user or self.teacher)
        return self.client.post(
            f'/api/documents/{doc["id"]}/transition/',
            {"action": action, "version": doc["version"], "comment": comment},
            format="json",
        )


class AuthTests(Base):
    def test_csrf_login_logout_and_expired_session(self):
        c = APIClient(enforce_csrf_checks=True)
        self.assertEqual(c.get("/api/auth/me/").status_code, 401)
        self.assertEqual(
            c.post(
                "/api/auth/login/",
                {"username": "qa_teacher", "password": "Test-Password-491!"},
                format="json",
            ).status_code,
            403,
        )
        token = c.get("/api/auth/csrf/").data["csrfToken"]
        c.credentials(HTTP_X_CSRFTOKEN=token)
        self.assertIn(
            c.post(
                "/api/auth/login/",
                {"username": "qa_teacher", "password": "bad"},
                format="json",
            ).status_code,
            [400, 401],
        )
        self.assertEqual(
            c.post(
                "/api/auth/login/",
                {"username": "qa_teacher", "password": "Test-Password-491!"},
                format="json",
            ).status_code,
            200,
        )
        self.assertEqual(c.get("/api/auth/me/").status_code, 200)
        c.credentials()
        self.assertEqual(
            c.post("/api/documents/", {}, format="json").status_code, 403
        )
        c.credentials(
            HTTP_X_CSRFTOKEN=c.get("/api/auth/csrf/").data["csrfToken"]
        )
        self.assertEqual(
            c.post("/api/auth/logout/", {}, format="json").status_code, 204
        )
        self.assertEqual(c.get("/api/auth/me/").status_code, 401)
        c.cookies["sessionid"] = "expired-session-id"
        self.assertEqual(c.get("/api/auth/me/").status_code, 401)

    def test_inactive_login(self):
        self.teacher.is_active = False
        self.teacher.save()
        c = APIClient(enforce_csrf_checks=True)
        c.credentials(
            HTTP_X_CSRFTOKEN=c.get("/api/auth/csrf/").data["csrfToken"]
        )
        self.assertIn(
            c.post(
                "/api/auth/login/",
                {"username": "qa_teacher", "password": "Test-Password-491!"},
                format="json",
            ).status_code,
            [400, 401],
        )


class PermissionTests(Base):
    def test_other_teacher_direct_endpoints_and_role_escalation(self):
        doc = self.create()
        self.client.force_authenticate(self.other)
        for suffix in ["", "preview/", "export/"]:
            self.assertEqual(
                self.client.get(
                    f'/api/documents/{doc["id"]}/{suffix}'
                ).status_code,
                404,
            )
        self.assertEqual(
            self.client.patch(
                f'/api/documents/{doc["id"]}/',
                {"title": "Hack", "version": 1},
                format="json",
            ).status_code,
            404,
        )
        self.assertEqual(
            self.transition(doc, "submit", self.other).status_code, 404
        )
        self.assertEqual(self.client.get("/api/documents/").data["count"], 0)
        self.assertEqual(
            self.client.patch(
                f"/api/users/{self.other.pk}/",
                {"role": "admin"},
                format="json",
            ).status_code,
            403,
        )
        self.other.refresh_from_db()
        self.assertEqual(self.other.role, "teacher")

    def test_protected_fields_and_manager_edit(self):
        doc = self.create(
            owner=self.other.pk,
            status="completed",
            version=999,
            completed_at="2020-01-01T00:00:00Z",
        )
        self.assertEqual(doc["owner"]["id"], self.teacher.pk)
        self.assertEqual(doc["status"], "draft")
        self.assertEqual(doc["version"], 1)
        self.assertIsNone(doc["completed_at"])
        self.client.force_authenticate(self.manager)
        self.assertEqual(
            self.client.get(f'/api/documents/{doc["id"]}/').status_code, 200
        )
        self.assertEqual(
            self.client.patch(
                f'/api/documents/{doc["id"]}/',
                {"title": "Hack", "version": 1},
                format="json",
            ).status_code,
            403,
        )


class ValidationTests(Base):
    def test_invalid_fields_and_boundaries(self):
        cases = [
            ("text", ""),
            ("text", "x" * 31),
            ("amount", 0),
            ("amount", 11),
            ("amount", "oops"),
            ("date", "2026-99-99"),
            ("choice", "В"),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                data = self.data()
                data[key] = value
                self.assertEqual(
                    self.client.post(
                        "/api/documents/",
                        {
                            "title": "Тест",
                            "template": self.template.pk,
                            "data": data,
                        },
                        format="json",
                    ).status_code,
                    400,
                )
        for number in [1, 10]:
            data = self.data()
            data.update(text="x" * 30, amount=number)
            self.create(data=data)

    def test_text_roundtrip_and_escaped_preview(self):
        data = self.data()
        data["body"] = '<script>alert("x")</script> & українська'
        doc = self.create(data=data)
        self.assertEqual(doc["data"]["body"], data["body"])
        html = self.client.get(f'/api/documents/{doc["id"]}/preview/').data[
            "html"
        ]
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class TemplateTests(Base):
    def test_schema_required_on_create_but_optional_on_partial_update(self):
        self.client.force_authenticate(self.admin)
        for fields in [
            {},
            {"schema": []},
            {"schema": [{"name": "broken", "type": "code"}]},
        ]:
            with self.subTest(fields=fields):
                response = self.client.post(
                    "/api/templates/",
                    {"name": "QA schema contract", **fields},
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn("schema", response.data)
        created = self.client.post(
            "/api/templates/",
            {"name": "QA valid schema", "schema": self.template.schema},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        updated = self.client.patch(
            f'/api/templates/{created.data["id"]}/',
            {"description": "Only metadata changed"},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["schema"], created.data["schema"])
        self.assertEqual(updated.data["description"], "Only metadata changed")

    def test_seed_is_idempotent_and_templates_differ(self):
        call_command("seed_templates", verbosity=0)
        rows = list(
            Template.objects.exclude(pk=self.template.pk).order_by("pk")
        )
        self.assertGreaterEqual(len(rows), 5)
        self.assertGreaterEqual(len({str(t.schema) for t in rows}), 5)
        first = rows[0]
        first.description = "QA custom description must survive seed"
        first.save()
        call_command("seed_templates", verbosity=0)
        self.assertEqual(Template.objects.count(), len(rows) + 1)
        first.refresh_from_db()
        self.assertEqual(
            first.description, "QA custom description must survive seed"
        )

    def test_snapshot_preserved(self):
        doc = self.create()
        self.client.force_authenticate(self.admin)
        result = self.client.patch(
            f"/api/templates/{self.template.pk}/",
            {"name": "Змінена назва", "schema": self.template.schema},
            format="json",
        )
        self.assertEqual(result.status_code, 200, result.data)
        self.assertGreater(result.data["version"], 1)
        old = self.client.get(f'/api/documents/{doc["id"]}/').data
        self.assertEqual(old["template_snapshot"], doc["template_snapshot"])

    def test_template_admin_only(self):
        self.assertEqual(
            self.client.post(
                "/api/templates/",
                {"name": "Hack", "schema": []},
                format="json",
            ).status_code,
            403,
        )


class LifecycleTests(Base):
    def test_full_alternative_cycle_and_completed_immutability(self):
        doc = self.create()
        doc = self.transition(doc, "submit").data
        self.assertEqual(doc["status"], "submitted")
        self.assertEqual(
            self.transition(doc, "return", self.manager, " ").status_code, 400
        )
        doc = self.transition(
            doc, "return", self.manager, "Уточніть зміст"
        ).data
        self.assertEqual(doc["status"], "returned")
        self.client.force_authenticate(self.teacher)
        response = self.client.patch(
            f'/api/documents/{doc["id"]}/',
            {
                "title": "Виправлено",
                "data": self.data(),
                "version": doc["version"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        doc = self.transition(response.data, "submit").data
        doc = self.transition(doc, "approve", self.manager).data
        self.assertEqual(doc["status"], "approved")
        doc = self.transition(doc, "complete").data
        self.assertEqual(doc["status"], "completed")
        self.assertIsNotNone(doc["completed_at"])
        row = Document.objects.get(pk=doc["id"])
        frozen_age = row.age_seconds
        with patch(
            "core.models.timezone.now",
            return_value=timezone.now() + timedelta(days=5),
        ):
            self.assertEqual(row.age_seconds, frozen_age)
        self.assertEqual(
            self.client.patch(
                f'/api/documents/{doc["id"]}/',
                {"title": "Illegal", "version": doc["version"]},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(self.transition(doc, "submit").status_code, 400)
        events = doc["events"]
        self.assertTrue(
            any(
                e["comment"] == "Уточніть зміст"
                and e["actor"]["id"] == self.manager.pk
                for e in events
            )
        )
        self.assertTrue(all(e["created_at"] for e in events))

    def test_all_transition_edges(self):
        allowed = {
            "draft": {"submit"},
            "returned": {"submit"},
            "submitted": {"approve", "return"},
            "approved": {"complete"},
            "completed": set(),
        }
        for status, actions in allowed.items():
            for action in ["submit", "approve", "return", "complete"]:
                with self.subTest(status=status, action=action):
                    self.client.force_authenticate(self.teacher)
                    doc = self.create()
                    Document.objects.filter(pk=doc["id"]).update(status=status)
                    response = self.transition(
                        doc,
                        action,
                        (
                            self.manager
                            if action in ["approve", "return"]
                            else self.teacher
                        ),
                        "Причина",
                    )
                    self.assertEqual(
                        response.status_code,
                        200 if action in actions else 400,
                        response.data,
                    )

    def test_teacher_cannot_approve(self):
        doc = self.transition(self.create(), "submit").data
        self.assertEqual(self.transition(doc, "approve").status_code, 403)

    def test_stale_edit_and_transition_are_409(self):
        doc = self.create()
        current = self.client.patch(
            f'/api/documents/{doc["id"]}/',
            {"title": "Нова", "version": doc["version"]},
            format="json",
        )
        self.assertEqual(current.status_code, 200, current.data)
        count = DocumentEvent.objects.count()
        self.assertEqual(
            self.client.patch(
                f'/api/documents/{doc["id"]}/',
                {"title": "Стара", "version": doc["version"]},
                format="json",
            ).status_code,
            409,
        )
        self.assertEqual(self.transition(doc, "submit").status_code, 409)
        self.assertEqual(DocumentEvent.objects.count(), count)

    def test_status_event_atomic_rollback(self):
        doc = self.create()
        before = DocumentEvent.objects.count()
        with patch(
            "core.models.DocumentEvent.objects.create",
            side_effect=RuntimeError("QA simulated storage failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.transition(doc, "submit")
        row = Document.objects.get(pk=doc["id"])
        self.assertEqual(row.status, "draft")
        self.assertEqual(row.version, doc["version"])
        self.assertEqual(DocumentEvent.objects.count(), before)


class RegistryTests(Base):
    def test_combined_search_filter_sort_pagination_scope(self):
        for title in ["Заява А", "Заява Б", "Заява В"]:
            self.create(title=title)
        self.client.force_authenticate(self.other)
        self.create(title="Заява чужа")
        self.client.force_authenticate(self.teacher)
        today = timezone.localdate().isoformat()
        response = self.client.get(
            "/api/documents/",
            {
                "search": "Заява",
                "status": "draft",
                "template": self.template.pk,
                "created_from": today,
                "created_to": today,
                "ordering": "title",
                "page_size": 2,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(
            [d["title"] for d in response.data["results"]],
            ["Заява А", "Заява Б"],
        )
        self.assertIsNotNone(response.data["next"])
        self.assertEqual(
            self.client.get("/api/documents/", {"search": "qa_other"}).data[
                "count"
            ],
            0,
        )

    def test_analytics_scope_empty_and_period(self):
        empty = self.client.get("/api/analytics/").data
        self.assertEqual(empty["total"], 0)
        self.assertIsNone(empty["average_cycle_seconds"])
        draft = self.create()
        done = self.create()
        now = timezone.now()
        Document.objects.filter(pk=done["id"]).update(
            status="completed",
            created_at=now - timedelta(hours=2),
            completed_at=now,
        )
        self.client.force_authenticate(self.other)
        self.create()
        self.client.force_authenticate(self.teacher)
        today = timezone.localdate().isoformat()
        data = self.client.get(
            "/api/analytics/", {"date_from": today, "date_to": today}
        ).data
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["by_status"]["draft"], 1)
        self.assertEqual(data["by_status"]["completed"], 1)
        self.assertEqual(data["pending_approval"], 0)
        self.assertEqual(data["completed_in_period"], 1)
        self.assertAlmostEqual(data["average_cycle_seconds"], 7200, delta=1)
        self.assertEqual(
            self.client.get("/api/documents/", {"status": "completed"}).data[
                "count"
            ],
            1,
        )
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.get("/api/analytics/").data["total"], 3)


class ExportTests(Base):
    def test_zero_is_rendered(self):
        self.template.schema = [
            {
                "name": "zero",
                "label": "Число",
                "type": "number",
                "required": True,
                "min": 0,
            }
        ]
        self.template.save()
        doc = self.create(data={"zero": 0})
        html = self.client.get(f'/api/documents/{doc["id"]}/preview/').data[
            "html"
        ]
        self.assertIn("<td>0</td>", html)
        response = self.client.get(f'/api/documents/{doc["id"]}/export/')
        payload = (
            b"".join(response.streaming_content)
            if response.streaming
            else response.content
        )
        with ZipFile(BytesIO(payload)) as archive:
            self.assertIn(
                ">0</w:t>", archive.read("word/document.xml").decode()
            )

    def test_real_docx_unicode_and_no_status_mutation(self):
        doc = self.create()
        response = self.client.get(f'/api/documents/{doc["id"]}/export/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document",
            response["Content-Type"],
        )
        self.assertIn("attachment", response["Content-Disposition"])
        payload = (
            b"".join(response.streaming_content)
            if response.streaming
            else response.content
        )
        with ZipFile(BytesIO(payload)) as archive:
            self.assertIn("[Content_Types].xml", archive.namelist())
            xml = archive.read("word/document.xml").decode()
            self.assertIn("Українська заява", xml)
            self.assertIn("Тестова заява", xml)
            self.assertIn("<w:tbl", xml)
        current = self.client.get(f'/api/documents/{doc["id"]}/').data
        self.assertEqual(current["status"], doc["status"])
        self.assertEqual(current["version"], doc["version"])
        self.assertEqual(current["events"], doc["events"])
