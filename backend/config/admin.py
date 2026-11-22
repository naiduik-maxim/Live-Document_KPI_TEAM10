"""Окрема консоль обслуговування для суперкористувача Django."""

from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig


class MaintenanceAdminSite(AdminSite):
    def has_permission(self, request):
        return super().has_permission(request) and request.user.is_superuser


class MaintenanceAdminConfig(AdminConfig):
    default_site = "config.admin.MaintenanceAdminSite"
