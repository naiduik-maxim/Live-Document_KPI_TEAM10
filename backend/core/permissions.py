"""Server-side role permissions shared by API endpoints."""

from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Перевіряти серверну роль, незалежно від доступних кнопок UI."""

    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and request.user.effective_role == "admin"
        )
