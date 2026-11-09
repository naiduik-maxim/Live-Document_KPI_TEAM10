from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, tag
from docx import Document as WordDocument
from rest_framework.exceptions import PermissionDenied, ValidationError

from ..models import DocumentEvent, Template
from ..rendering import render_docx, render_html
from ..serializers import CreateDocumentSerializer, UserAdminSerializer
from ..services import (
    Conflict,
    create_document,
    edit_document,
    transition_document,
)
from ..validation import validate_data, validate_schema


class BusinessLogicTests(TestCase):
    def setUp(self):
        self.teacher = get_user_model().objects.create_user(
            "author", password="testing-only-pass"
        )
        self.manager = get_user_model().objects.create_user(
            "manager", password="testing-only-pass", role="manager"
        )
        self.template = Template.objects.create(
            name="Тест",
            schema=[
                {
                    "name": "text",
                    "label": "Текст",
                    "type": "textarea",
                    "required": True,
                    "max_length": 50,
                }
            ],
        )
        self.doc = create_document(
            self.teacher,
            "Документ",
            self.template,
            {"text": "Українська мова\n- Пункт"},
        )

    @tag("module3")
    def test_cycle_and_frozen_age(self):
        d = transition_document(self.teacher, self.doc.id, 1, "submit")
        d = transition_document(
            self.manager, d.id, d.version, "return", "Доповніть"
        )
        d = edit_document(
            self.teacher, d.id, d.version, data={"text": "Виправлено"}
        )
        d = transition_document(self.teacher, d.id, d.version, "submit")
        d = transition_document(self.manager, d.id, d.version, "approve")
        d = transition_document(self.teacher, d.id, d.version, "complete")
        self.assertEqual(d.status, "completed")
        self.assertIsNotNone(d.completed_at)
        self.assertEqual(d.age_seconds, d.age_seconds)
        self.assertEqual(d.events.count(), 7)
        with self.assertRaises(ValidationError):
            edit_document(self.teacher, d.id, d.version, title="Зміна")

    @tag("module3")
    def test_conflict_and_permissions(self):
        edit_document(self.teacher, self.doc.id, 1, title="Нова назва")
        with self.assertRaises(Conflict):
            edit_document(self.teacher, self.doc.id, 1, title="Застаріло")
        with self.assertRaises(PermissionDenied):
            transition_document(self.teacher, self.doc.id, 2, "approve")
        with self.assertRaises(ValidationError):
            transition_document(self.manager, self.doc.id, 2, "return", "")

    @tag("module3")
    def test_atomic_history_failure(self):
        with patch.object(
            DocumentEvent.objects,
            "create",
            side_effect=RuntimeError("history failure"),
        ):
            with self.assertRaises(RuntimeError):
                transition_document(self.teacher, self.doc.id, 1, "submit")
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, "draft")
        self.assertEqual(self.doc.version, 1)

    @tag("module2")
    def test_snapshot_and_docx(self):
        self.template.schema = []
        self.template.save()
        edit_document(
            self.teacher,
            self.doc.id,
            1,
            data={"text": "<script>test</script>"},
        )
        self.doc.refresh_from_db()
        self.assertNotIn("<script>", render_html(self.doc))
        doc = WordDocument(render_docx(self.doc))
        self.assertIn(
            "<script>test</script>", "\n".join(p.text for p in doc.paragraphs)
        )

    @tag("module2")
    def test_validation(self):
        for data in [
            {},
            {"text": " "},
            {"text": "x" * 51},
            {"text": 3},
            {"text": "ok", "unknown": "bad"},
        ]:
            with self.assertRaises(ValidationError):
                create_document(self.teacher, "Bad", self.template, data)

    @tag("module4")
    def test_legacy_xml_controls_render_consistently(self):
        self.doc.title = "Заголовок\x01 <script>"
        self.doc.template_snapshot["name"] = "Назва\x02"
        self.doc.template_snapshot["description"] = "Приклад\ud800"
        preview = render_html(self.doc)
        word = WordDocument(render_docx(self.doc))
        self.assertIn("Заголовок &lt;script&gt;", preview)
        self.assertNotIn("\x01", preview)
        self.assertNotIn("\ud800", preview)
        self.assertEqual(word.paragraphs[0].text, "Заголовок <script>")
        self.assertEqual(word.paragraphs[1].text, "Назва")
        self.assertEqual(word.paragraphs[2].text, "Приклад")

    @tag("module1")
    def test_superuser_api_role_is_consistent(self):
        user = get_user_model().objects.create_superuser(
            "root", password="testing-only-pass"
        )
        self.assertEqual(UserAdminSerializer(user).data["role"], "admin")
        update = UserAdminSerializer(
            user, data={"role": "teacher"}, partial=True
        )
        self.assertFalse(update.is_valid())
        self.assertIn("role", update.errors)
        update = UserAdminSerializer(
            user, data={"first_name": "Адміністратор"}, partial=True
        )
        self.assertTrue(update.is_valid(), update.errors)
        update.save()
        self.assertEqual(user.effective_role, "admin")

    @tag("module2")
    def test_non_xml_text_and_huge_numbers_are_validation_errors(self):
        for value in ["Bad\x01", "Bad\ud800", "Bad\uffff"]:
            serializer = CreateDocumentSerializer(
                data={
                    "title": value,
                    "template": self.template.pk,
                    "data": {"text": "ok"},
                }
            )
            self.assertFalse(serializer.is_valid())
            self.assertIn("title", serializer.errors)
            with self.assertRaises(ValidationError):
                validate_data({"text": value}, self.template.schema)
        number_schema = [{"name": "n", "label": "Number", "type": "number"}]
        with self.assertRaises(ValidationError):
            validate_data({"n": 10**400}, number_schema)
        number_schema[0]["min"] = 10**400
        with self.assertRaises(ValidationError):
            validate_schema(number_schema)
