from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

def _normalize_text(value: Any) -> str:
    """Нормализует строковое значение для сравнения."""
    if not isinstance(value, str):
        return str(value)

    return re.sub(
        r"\s+",
        " ",
        value.strip().casefold(),
    )

def _normalize_currency(value: Any) -> str:
    """Нормализует валюту для сравнения."""
    return _normalize_text(value).upper()

def _normalize_quantity(value: Any) -> Any:
    """Нормализует количество для сравнения."""
    if isinstance(value, str):
        normalized = re.sub(r"[\s\u00A0]", "", value)

        if normalized.isdigit():
            return int(normalized)

    return value

def _add_mismatch_risk(
    risks: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    field_name: str,
    risk_type: str,
    title: str,
    normalizer: Callable[[Any], Any],
    severity: str = "high",
) -> None:
    """Добавляет риск, если значение поля отличается в документах."""

    values: dict[str, Any] = {}
    normalized_values: set[Any] = set()

    for index, document in enumerate(documents, start=1):
        fields = document.get("fields", {})

        if not isinstance(fields, dict):
            continue

        if field_name not in fields:
            continue

        value = fields[field_name]

        if value is None:
            continue

        if isinstance(value, str) and not value.strip():
            continue

        file_name = document.get("file_name")

        if not isinstance(file_name, str) or not file_name.strip():
            file_name = f"document_{index}"

        normalized_value = normalizer(value)

        try:
            normalized_values.add(normalized_value)
        except TypeError:
            # Защита от случайных списков или словарей
            normalized_value = repr(normalized_value)
            normalized_values.add(normalized_value)

        values[file_name] = value

    if len(normalized_values) > 1:
        risks.append(
            {
                "risk_type": risk_type,
                "severity": severity,
                "title": title,
                "details": values,
            }
        )

def check_consistency(
    documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Проверяет согласованность данных между документами.

    Проверяются поля:
    - quantity;
    - product;
    - currency.
    """
    if not isinstance(documents, list):
        raise TypeError(
            "Список документов должен быть массивом"
        )

    valid_documents: list[dict[str, Any]] = []

    for index, document in enumerate(documents, start=1):
        if not isinstance(document, dict):
            raise TypeError(
                f"Документ #{index} должен быть объектом"
            )

        fields = document.get("fields", {})

        if fields is None:
            fields = {}

        if not isinstance(fields, dict):
            raise TypeError(
                f"Поле 'fields' документа #{index} "
                "должно быть объектом"
            )

        valid_documents.append(
            {
                **document,
                "fields": fields,
            }
        )

    risks: list[dict[str, Any]] = []

    _add_mismatch_risk(
        risks=risks,
        documents=valid_documents,
        field_name="quantity",
        risk_type="quantity_mismatch",
        title="Несогласованное количество",
        normalizer=_normalize_quantity,
    )

    _add_mismatch_risk(
        risks=risks,
        documents=valid_documents,
        field_name="product",
        risk_type="product_mismatch",
        title="Несогласованная продукция",
        normalizer=_normalize_text,
    )

    _add_mismatch_risk(
        risks=risks,
        documents=valid_documents,
        field_name="currency",
        risk_type="currency_mismatch",
        title="Несогласованная валюта",
        normalizer=_normalize_currency,
    )

    return risks
