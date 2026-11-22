"""Окремі поля запитів і службові поля відповідей API."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Document, DocumentEvent, Template, User
from .validation import validate_schema, validate_xml_text


class UserSerializer(serializers.ModelSerializer):
    """Публічне представлення користувача без запису ролі або пароля."""

    role = serializers.CharField(source="effective_role", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "is_active",
        ]


class UserAdminSerializer(serializers.ModelSerializer):
    """Керування обліковими записами через endpoint з правами admin."""

    password = serializers.CharField(
        write_only=True, required=False, trim_whitespace=False
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "first_name",
            "last_name",
            "email",
            "position",
            "phone",
            "role",
            "is_active",
        ]

    def validate_position(self, value):
        return validate_xml_text(value)

    def validate_phone(self, value):
        return validate_xml_text(value)

    def validate(self, attrs):
        if (
            self.instance
            and self.instance.is_superuser
            and attrs.get("role", "admin") != "admin"
        ):
            raise serializers.ValidationError(
                {
                    "role": (
                        "Роль суперкористувача змінюється "
                        "лише в Django Admin."
                    )
                }
            )
        if not self.instance and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Потрібен пароль."})
        if attrs.get("password"):
            user = self.instance or User(username=attrs.get("username", ""))
            try:
                validate_password(attrs["password"], user)
            except DjangoValidationError as e:
                raise serializers.ValidationError({"password": e.messages})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["role"] = instance.effective_role
        return data

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        # Пароль проходить хешування Django, а не звичайне присвоєння.
        password = validated_data.pop("password", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class TemplateSerializer(serializers.ModelSerializer):
    """Перевірити схему полів до збереження нової версії шаблону."""

    schema = serializers.JSONField(required=True)

    class Meta:
        model = Template
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "version",
            "schema",
        ]
        read_only_fields = ["version"]

    def validate_schema(self, value):
        return validate_schema(value)

    def validate_name(self, value):
        return validate_xml_text(value)

    def validate_description(self, value):
        return validate_xml_text(value)


class EventSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)

    class Meta:
        model = DocumentEvent
        fields = [
            "id",
            "actor",
            "from_status",
            "to_status",
            "comment",
            "created_at",
        ]


class DocumentSerializer(serializers.ModelSerializer):
    """Повертати стан документа; зміни виконує лише сервісний шар."""

    owner = UserSerializer(read_only=True)
    events = EventSerializer(many=True, read_only=True)
    age_seconds = serializers.FloatField(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "owner",
            "template",
            "template_snapshot",
            "data",
            "signatories",
            "status",
            "version",
            "created_at",
            "updated_at",
            "completed_at",
            "age_seconds",
            "events",
        ]
        read_only_fields = fields


class CreateDocumentSerializer(serializers.Serializer):
    """Приймати зміст; автор, статус і час визначаються сервером."""

    title = serializers.CharField(max_length=250)
    template = serializers.PrimaryKeyRelatedField(
        queryset=Template.objects.filter(is_active=True)
    )
    data = serializers.JSONField()

    def validate_title(self, value):
        return validate_xml_text(value)


class EditDocumentSerializer(serializers.Serializer):
    """Вимагати версію навіть під час часткового редагування."""

    title = serializers.CharField(max_length=250, required=False)
    data = serializers.JSONField(required=False)
    version = serializers.IntegerField(min_value=1)

    def validate_title(self, value):
        return validate_xml_text(value)


class TransitionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=["submit", "approve", "return", "complete"]
    )
    version = serializers.IntegerField(min_value=1)
    comment = serializers.CharField(
        max_length=5000, required=False, allow_blank=True, default=""
    )

    def validate_comment(self, value):
        return validate_xml_text(value)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)
