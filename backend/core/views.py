"""HTTP endpoints: валідація запитів і виклик доменних сервісів."""

from datetime import date

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.db.models.functions import TruncDate
from django.http import FileResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, Template, User
from .permissions import IsAdmin
from .rendering import render_docx, render_html
from .serializers import (
    CreateDocumentSerializer,
    DocumentSerializer,
    EditDocumentSerializer,
    LoginSerializer,
    TemplateSerializer,
    TransitionSerializer,
    UserAdminSerializer,
    UserSerializer,
)
from .services import (
    create_document,
    edit_document,
    transition_document,
    visible_documents,
)


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response({"status": "ok"})


class CsrfView(APIView):
    """Видати токен і cookie для входу та наступних змін через SPA."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    """Захистити також анонімний вхід від підміни сесії через CSRF."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get_authenticate_header(self, request):
        return "Session"

    @extend_schema(request=LoginSerializer, responses=UserSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Штатний backend Django відхиляє неактивні облікові записи.
        user = authenticate(request, **serializer.validated_data)
        if user is None:
            raise AuthenticationFailed("Невірне ім’я користувача або пароль.")
        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        logout(request)
        return Response(status=204)


class MeView(APIView):
    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    """Дозволити керування ролями лише адміністраторам на сервері."""

    permission_classes = [IsAdmin]
    serializer_class = UserAdminSerializer
    queryset = User.objects.order_by("username", "id")
    http_method_names = ["get", "post", "patch", "head", "options"]


class TemplateViewSet(viewsets.ModelViewSet):
    serializer_class = TemplateSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        return (
            [IsAdmin()]
            if self.action in ["create", "partial_update"]
            else super().get_permissions()
        )

    def get_queryset(self):
        qs = Template.objects.order_by("name", "id")
        return (
            qs
            if self.request.user.is_authenticated
            and self.request.user.effective_role == "admin"
            else qs.filter(is_active=True)
        )

    @transaction.atomic
    def perform_update(self, serializer):
        # Блокування запобігає втраті інкремента версії шаблону.
        template = Template.objects.select_for_update().get(
            pk=serializer.instance.pk
        )
        serializer.instance = template
        serializer.save(version=template.version + 1)


def parse_date_param(request, key):
    """Повернути дату фільтра або контрольовану помилку API."""
    value = request.query_params.get(key)
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationError({key: "Очікується дата YYYY-MM-DD."})


class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """Застосувати права до прямого URL перед будь-якою операцією."""

    serializer_class = DocumentSerializer

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Document.objects.none()
        # Одна область доступу діє і для списку, і для get_object().
        qs = visible_documents(self.request.user)
        if self.action != "list":
            return qs
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(owner__username__icontains=search)
                | Q(owner__first_name__icontains=search)
                | Q(owner__last_name__icontains=search)
                | Q(template__name__icontains=search)
            )
        status_value = self.request.query_params.get("status")
        if status_value:
            if status_value not in dict(Document.STATUSES):
                raise ValidationError({"status": "Невідомий статус."})
            qs = qs.filter(status=status_value)
        template = self.request.query_params.get("template")
        if template:
            if not template.isdigit():
                raise ValidationError({"template": "Очікується ID."})
            qs = qs.filter(template_id=template)
        start = parse_date_param(self.request, "created_from")
        end = parse_date_param(self.request, "created_to")
        if start and end and start > end:
            raise ValidationError(
                {"created_to": "Кінець періоду раніше початку."}
            )
        if start:
            qs = qs.filter(created_at__date__gte=start)
        if end:
            qs = qs.filter(created_at__date__lte=end)
        ordering = self.request.query_params.get("ordering", "-created_at")
        if ordering not in [
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
            "title",
            "-title",
        ]:
            raise ValidationError({"ordering": "Непідтримуване сортування."})
        # ID стабілізує сторінки за однакових значень сортування.
        return qs.order_by(ordering, "id")

    @extend_schema(
        request=CreateDocumentSerializer, responses={201: DocumentSerializer}
    )
    def create(self, request):
        serializer = CreateDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = create_document(request.user, **serializer.validated_data)
        return Response(DocumentSerializer(document).data, status=201)

    @extend_schema(
        request=EditDocumentSerializer, responses=DocumentSerializer
    )
    def partial_update(self, request, pk=None):
        document = self.get_object()
        serializer = EditDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = edit_document(
            request.user, document.pk, **serializer.validated_data
        )
        return Response(DocumentSerializer(document).data)

    @extend_schema(request=TransitionSerializer, responses=DocumentSerializer)
    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        document = self.get_object()
        serializer = TransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = transition_document(
            request.user, document.pk, **serializer.validated_data
        )
        return Response(DocumentSerializer(document).data)

    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        return Response({"html": render_html(self.get_object())})

    @extend_schema(
        responses={
            (
                200,
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document",
            ): OpenApiTypes.BINARY
        }
    )
    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        # get_object() перевіряє доступ; експорт не змінює стан.
        document = self.get_object()
        return FileResponse(
            render_docx(document),
            as_attachment=True,
            filename=f"Документ-{document.pk}.docx",
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
        )


class AnalyticsView(APIView):
    """Обчислити показники в БД для доступних користувачу документів."""

    @extend_schema(
        responses=OpenApiTypes.OBJECT,
        parameters=[
            OpenApiParameter("date_from", OpenApiTypes.DATE),
            OpenApiParameter("date_to", OpenApiTypes.DATE),
        ],
    )
    def get(self, request):
        qs = visible_documents(request.user)
        start = parse_date_param(request, "date_from")
        end = parse_date_param(request, "date_to")
        if start and end and start > end:
            raise ValidationError(
                {"date_to": "Кінець періоду раніше початку."}
            )
        # Для порожніх статусів повертаємо явний нуль.
        by_status = {key: 0 for key, _ in Document.STATUSES}
        by_status.update(
            {
                row["status"]: row["n"]
                for row in qs.values("status").annotate(n=Count("id"))
            }
        )
        completed = qs.filter(status="completed", completed_at__isnull=False)
        # За контрактом середній цикл охоплює всі доступні завершення.
        mean = completed.aggregate(
            value=Avg(
                ExpressionWrapper(
                    F("completed_at") - F("created_at"),
                    output_field=DurationField(),
                )
            )
        )["value"]
        # Період обмежує завершення та тренд; загальні лічильники повні.
        trend = qs
        if start:
            completed = completed.filter(completed_at__date__gte=start)
            trend = trend.filter(created_at__date__gte=start)
        if end:
            completed = completed.filter(completed_at__date__lte=end)
            trend = trend.filter(created_at__date__lte=end)
        creation = list(
            trend.annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )
        return Response(
            {
                "total": sum(by_status.values()),
                "by_status": by_status,
                "pending_approval": by_status["submitted"],
                "completed_in_period": completed.count(),
                "average_cycle_seconds": (
                    mean.total_seconds() if mean is not None else None
                ),
                "creation_trend": creation,
            }
        )
