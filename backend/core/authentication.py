"""Сесійна автентифікація DRF зі збереженням штатної CSRF-перевірки."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import (
    SessionAuthentication as BaseSessionAuthentication,
)


class SessionAuthentication(BaseSessionAuthentication):
    """Повертати 401 для відсутньої сесії через challenge-заголовок."""

    def authenticate_header(self, request):
        return "Session"


class SessionScheme(OpenApiAuthenticationExtension):
    """Описати session cookie та вимогу CSRF для клієнтів OpenAPI."""

    target_class = "core.authentication.SessionAuthentication"
    name = "cookieAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "sessionid",
            "description": (
                "Django session; unsafe requests require X-CSRFToken header."
            ),
        }
