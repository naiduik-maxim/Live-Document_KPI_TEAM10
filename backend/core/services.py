"""Права, переходи статусів і атомарні зміни разом з аудитом."""

from copy import deepcopy

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import (
    APIException,
    PermissionDenied,
    ValidationError,
)

from .models import Document, DocumentEvent
from .validation import validate_data


class Conflict(APIException):
    """Повідомити клієнту про спробу змінити застарілу версію."""

    status_code = 409
    default_detail = "Документ змінено іншим користувачем. Оновіть сторінку."


def visible_documents(user):
    """Обмежити реєстр, деталі, експорт і статистику за роллю."""
    qs = Document.objects.select_related("owner", "template").prefetch_related(
        "events__actor"
    )
    require_document_role(user)
    return qs if user.effective_role == "manager" else qs.filter(owner=user)


def require_document_role(user):
    if user.effective_role not in ("teacher", "manager"):
        raise PermissionDenied(
            "Робота з документами доступна викладачам і керівникам."
        )


def check_version(document, version):
    """Відхилити перезапис даних, яких користувач ще не бачив."""
    if document.version != version:
        raise Conflict()


@transaction.atomic
def create_document(user, title, template, data):
    """Створити документ і початкову подію в одній транзакції."""
    require_document_role(user)
    validate_data(data, template.schema)
    # Копія JSON не ділить вкладені значення з поточним шаблоном.
    snapshot = {
        k: deepcopy(getattr(template, k))
        for k in ["name", "description", "version", "schema"]
    }
    document = Document.objects.create(
        owner=user,
        title=title,
        template=template,
        template_snapshot=snapshot,
        data=data,
        signatories={
            "executor_name": user.get_full_name() or user.get_username(),
            "executor_position": user.position,
            "executor_phone": user.phone,
            "executor_email": user.email,
        },
    )
    DocumentEvent.objects.create(
        document=document,
        actor=user,
        from_status="",
        to_status="draft",
        comment="Документ створено",
    )
    return document


@transaction.atomic
def edit_document(user, document_id, version, **changes):
    """Зберегти дозволені поля, нову версію та подію редагування."""
    # Блокування серіалізує записи; version виявляє застарілий запит.
    require_document_role(user)
    document = Document.objects.select_for_update().get(pk=document_id)
    if document.owner_id != user.id:
        raise PermissionDenied("Редагувати можна лише власні документи.")
    check_version(document, version)
    if document.status not in ["draft", "returned"]:
        raise ValidationError(
            {
                "detail": (
                    "Редагування можливе лише для чернетки "
                    "або документа на доопрацюванні."
                )
            }
        )
    if "data" in changes:
        # Перевіряємо історичну схему саме цього документа.
        validate_data(changes["data"], document.template_snapshot["schema"])
    for key in ["title", "data"]:
        if key in changes:
            setattr(document, key, changes[key])
    document.version += 1
    document.save()
    DocumentEvent.objects.create(
        document=document,
        actor=user,
        from_status=document.status,
        to_status=document.status,
        comment="Документ відредаговано",
    )
    return document


@transaction.atomic
def transition_document(user, document_id, version, action, comment=""):
    """Перевірити роль і маршрут та атомарно записати статус й аудит."""
    # Рядок залишається заблокованим до завершення atomic-транзакції.
    require_document_role(user)
    document = Document.objects.select_for_update().get(pk=document_id)
    role = user.effective_role
    if action == "submit" and document.owner_id != user.id:
        raise PermissionDenied("Надсилати документ може лише автор.")
    if action in ["approve", "return"] and role != "manager":
        raise PermissionDenied("Потрібні права керівника.")
    if (
        action == "complete"
        and document.owner_id != user.id
        and role != "manager"
    ):
        raise PermissionDenied()
    check_version(document, version)
    # Завершений стан не має вихідних переходів у звичайному API.
    transitions = {
        "submit": (["draft", "returned"], "submitted"),
        "approve": (["submitted"], "approved"),
        "return": (["submitted"], "returned"),
        "complete": (["approved"], "completed"),
    }
    if action not in transitions:
        raise ValidationError({"action": "Невідома дія."})
    allowed, target = transitions[action]
    if document.status not in allowed:
        raise ValidationError(
            {"detail": "Перехід із поточного статусу заборонено."}
        )
    if action == "return" and not comment.strip():
        raise ValidationError({"comment": "Вкажіть причину повернення."})
    previous = document.status
    document.status = target
    document.version += 1
    if target == "approved":
        document.signatories = {
            **document.signatories,
            "manager_name": user.get_full_name() or user.get_username(),
        }
    elif target == "completed":
        document.completed_at = timezone.now()
    document.save()
    # Збій запису події відкочує також зміну статусу та версії.
    DocumentEvent.objects.create(
        document=document,
        actor=user,
        from_status=previous,
        to_status=target,
        comment=comment,
    )
    return document
