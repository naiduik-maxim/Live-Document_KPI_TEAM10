"""Спільні обмеження схем і даних для API та Django Admin."""

import math
import re
from datetime import date

from rest_framework.exceptions import ValidationError


def validate_xml_text(value):
    """Відхилити символи, несумісні з XML документа Word."""
    if re.search(
        r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]", value
    ):
        raise ValidationError("Недопустимі керуючі символи.")
    return value


def finite_number(value):
    """Відрізнити скінченні числа від bool, NaN та нескінченності."""
    try:
        return type(value) in [int, float] and math.isfinite(value)
    except OverflowError:
        return False


def validate_schema(schema):
    """Дозволити лише відомі типи полів і коректні межі їх значень."""
    if not isinstance(schema, list) or not 1 <= len(schema) <= 50:
        raise ValidationError("Схема повинна містити 1–50 полів.")
    names = set()
    for field in schema:
        if not isinstance(field, dict):
            raise ValidationError("Поле має бути об’єктом.")
        name = field.get("name", "")
        if (
            not isinstance(name, str)
            or not re.fullmatch(r"[a-z][a-z0-9_]{0,49}", name)
            or name in names
        ):
            raise ValidationError(
                "Імена полів мають бути унікальними "
                "латинськими ідентифікаторами."
            )
        names.add(name)
        if (
            not isinstance(field.get("label"), str)
            or not 1 <= len(field["label"].strip()) <= 200
        ):
            raise ValidationError("Потрібна назва поля до 200 символів.")
        validate_xml_text(field["label"])
        if field.get("type") not in [
            "text",
            "textarea",
            "number",
            "date",
            "select",
        ]:
            raise ValidationError("Непідтримуваний тип поля.")
        if not isinstance(field.get("required", False), bool):
            raise ValidationError("required має бути boolean.")
        if "max_length" in field and (
            type(field["max_length"]) is not int
            or not 1 <= field["max_length"] <= 20000
        ):
            raise ValidationError("max_length: 1–20000.")
        for bound in ["min", "max"]:
            if bound in field and not finite_number(field[bound]):
                raise ValidationError("Межа має бути скінченним числом.")
        if "min" in field and "max" in field and field["min"] > field["max"]:
            raise ValidationError("min перевищує max.")
        if field["type"] == "select":
            choices = field.get("choices")
            if (
                not isinstance(choices, list)
                or not 1 <= len(choices) <= 100
                or any(
                    not isinstance(c, str) or not c or len(c) > 200
                    for c in choices
                )
                or len(set(choices)) != len(choices)
            ):
                raise ValidationError(
                    "Список вибору має містити унікальні текстові значення."
                )
            for choice in choices:
                validate_xml_text(choice)
    return schema


def validate_data(data, schema):
    """Перевірити всі значення проти поточної або збереженої схеми."""
    if not isinstance(data, dict):
        raise ValidationError({"data": "Очікується об’єкт."})
    errors = {}
    names = {f["name"] for f in schema}
    if set(data) - names:
        errors["unknown"] = "Невідомі поля: " + ", ".join(
            sorted(set(data) - names)
        )
    for f in schema:
        key = f["name"]
        value = data.get(key)
        if value is None or value == "":
            if f.get("required"):
                errors[key] = "Обов’язкове поле."
            continue
        kind = f["type"]
        if kind == "number":
            if not finite_number(value):
                errors[key] = "Введіть число."
            elif ("min" in f and value < f["min"]) or (
                "max" in f and value > f["max"]
            ):
                errors[key] = "Число поза допустимими межами."
        elif not isinstance(value, str):
            errors[key] = "Очікується текст."
        elif len(value) > f.get("max_length", 20000):
            errors[key] = "Перевищено максимальну довжину."
        elif f.get("required") and not value.strip():
            errors[key] = "Обов’язкове поле."
        elif kind == "select" and value not in f.get("choices", []):
            errors[key] = "Недопустиме значення."
        elif kind == "date":
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    raise ValueError()
                date.fromisoformat(value)
            except ValueError:
                errors[key] = "Введіть коректну дату YYYY-MM-DD."
        # Відхиляємо несумісний із XML 1.0 текст ще до експорту.
        if isinstance(value, str):
            try:
                validate_xml_text(value)
            except ValidationError:
                errors[key] = "Недопустимі керуючі символи."
    if errors:
        raise ValidationError({"data": errors})
    return data
