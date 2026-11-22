"""Адміністрування користувачів і шаблонів та перегляд аудиту."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from .models import Document, DocumentEvent, Template, User
from .validation import validate_schema


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Роль", {"fields": ("role",)}),
        ("Реквізити виконавця", {"fields": ("position", "phone")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Роль", {"fields": ("role",)}),
        (
            "Реквізити виконавця",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "position",
                    "phone",
                )
            },
        ),
    )


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    """Застосувати до схем ті самі обмеження, що й у REST API."""

    list_display = ["name", "version", "is_active"]
    readonly_fields = ["version"]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        def clean_schema(instance):
            try:
                return validate_schema(instance.cleaned_data["schema"])
            except DRFValidationError as e:
                raise ValidationError(str(e.detail))

        form.clean_schema = clean_schema
        return form

    def save_model(self, request, obj, form, change):
        if change:
            obj.version += 1
        super().save_model(request, obj, form, change)


@admin.register(Document, DocumentEvent)
class AuditReadOnlyAdmin(admin.ModelAdmin):
    """Не дозволяти обхід сервісних переходів і аудиту через Admin."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
