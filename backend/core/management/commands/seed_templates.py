"""Демонстраційні бланки; вони не є офіційними документами кафедри."""

from django.core.management.base import BaseCommand

from core.models import Template


def field(name, label, kind="text", **kwargs):
    """Побудувати опис обов'язкового поля демонстраційного шаблону."""
    return {
        "name": name,
        "label": label,
        "type": kind,
        "required": True,
        **kwargs,
    }


TEMPLATES = [
    (
        "Заява",
        [
            field("recipient", "Адресат", max_length=200),
            field("applicant", "ПІБ заявника", max_length=200),
            field("request", "Прошу", "textarea", max_length=4000),
            field("date", "Дата", "date"),
        ],
    ),
    (
        "Службова записка",
        [
            field("department", "Підрозділ", max_length=150),
            field("subject", "Тема", max_length=200),
            field(
                "priority",
                "Пріоритет",
                "select",
                choices=["Звичайний", "Терміновий"],
            ),
            field(
                "justification", "Обґрунтування", "textarea", max_length=6000
            ),
            field(
                "budget",
                "Очікувані витрати, грн",
                "number",
                min=0,
                max=10000000,
            ),
        ],
    ),
    (
        "Протокол засідання",
        [
            field("meeting_date", "Дата засідання", "date"),
            field("number", "Номер протоколу", max_length=30),
            field("chair", "Голова засідання", max_length=200),
            field(
                "attendees", "Кількість присутніх", "number", min=1, max=500
            ),
            field("agenda", "Порядок денний", "textarea", max_length=6000),
            field("decisions", "Ухвалили", "textarea", max_length=10000),
        ],
    ),
    (
        "Звіт про роботу",
        [
            field("period_start", "Початок періоду", "date"),
            field("period_end", "Кінець періоду", "date"),
            field("hours", "Відпрацьовані години", "number", min=0, max=10000),
            field(
                "activities", "Виконані роботи", "textarea", max_length=10000
            ),
            field(
                "outcome",
                "Результат",
                "select",
                choices=[
                    "Виконано",
                    "Частково виконано",
                    "Потребує продовження",
                ],
            ),
        ],
    ),
    (
        "Інструкція з охорони праці",
        [
            field("workplace", "Робоче місце", max_length=200),
            field(
                "risk",
                "Рівень ризику",
                "select",
                choices=["Низький", "Середній", "Високий"],
            ),
            field(
                "hazards", "Небезпечні чинники", "textarea", max_length=6000
            ),
            field(
                "safety_rules", "Правила безпеки", "textarea", max_length=10000
            ),
            field(
                "emergency",
                "Дії в аварійних ситуаціях",
                "textarea",
                max_length=6000,
            ),
            field("review_date", "Дата перегляду", "date"),
        ],
    ),
]


class Command(BaseCommand):
    """Додати відсутні приклади зі збереженням редагованих шаблонів."""

    help = "Створює п’ять демонстраційних шаблонів без перезапису існуючих."

    def handle(self, *args, **options):
        created = 0
        for name, schema in TEMPLATES:
            # Повторний запуск не перезаписує схеми й версії в базі.
            _, is_new = Template.objects.get_or_create(
                name=name,
                defaults={
                    "schema": schema,
                    "description": (
                        "Демонстраційний приклад. "
                        "Не є офіційним бланком кафедри ІПЗЕ."
                    ),
                },
            )
            created += is_new
        self.stdout.write(self.style.SUCCESS(f"Створено шаблонів: {created}"))
