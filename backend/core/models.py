"""Дані користувачів, версій шаблонів і життєвого циклу документів."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Обліковий запис Django з окремою прикладною роллю."""

    role = models.CharField(
        max_length=10,
        choices=[
            ("teacher", "Викладач"),
            ("manager", "Керівник"),
            ("admin", "Адміністратор"),
        ],
        default="teacher",
    )

    @property
    def effective_role(self):
        """Надати суперкористувачу адміністративні права застосунку."""
        return "admin" if self.is_superuser else self.role


class Template(models.Model):
    """Редагований опис полів для майбутніх документів."""

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    schema = models.JSONField(default=list)
    version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.name


class Document(models.Model):
    """Документ із власними даними та зафіксованою схемою шаблону."""

    STATUSES = [
        (v, v)
        for v in ["draft", "submitted", "returned", "approved", "completed"]
    ]
    owner = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="documents"
    )
    template = models.ForeignKey(Template, on_delete=models.PROTECT)
    # Знімок захищає старі документи від наступних змін шаблону.
    template_snapshot = models.JSONField()
    title = models.CharField(max_length=250)
    data = models.JSONField(default=dict)
    status = models.CharField(
        max_length=12, choices=STATUSES, default="draft", db_index=True
    )
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["template", "created_at"]),
        ]

    @property
    def age_seconds(self):
        """Зупинити відлік віку на збереженому моменті завершення."""
        return max(
            0,
            (self.completed_at or timezone.now()).timestamp()
            - self.created_at.timestamp(),
        )


class DocumentEvent(models.Model):
    """Подія аудиту, яку сервіс зберігає разом зі зміною документа."""

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="events"
    )
    actor = models.ForeignKey(User, on_delete=models.PROTECT)
    from_status = models.CharField(max_length=12, blank=True)
    to_status = models.CharField(max_length=12)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
