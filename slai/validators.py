from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from typing import Any

REQUIRED_FIELDS = (
    "supplier_name",
    "product_name",
    "quantity",
    "unit_price",
    "currency",
    "incoterm",
    "payment_terms",
)

def _get_value(
    deal: Any,
    field_name: str,
) -> Any:
    """Получает поле из словаря или объекта."""
    if isinstance(deal, Mapping):
        return deal.get(field_name)

    return getattr(deal, field_name, None)

def _is_empty(value: Any) -> bool:
    """Проверяет, является ли значение пустым."""
    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    if isinstance(value, bool):
        return False

    if isinstance(value, Real):
        return value == 0

    return False

def _is_positive_number(value: Any) -> bool:
    """Проверяет положительное числовое значение."""
    if isinstance(value, bool):
        return False

    if not isinstance(value, Real):
        return False

    return value > 0

def validate_deal(
    deal: Any,
) -> list[str]:
    """
    Возвращает список незаполненных или некорректных полей сделки.

    Поддерживаются:
    - объекты Deal;
    - словари;
    - другие объекты с атрибутами сделки.
    """
    if deal is None:
        return list(REQUIRED_FIELDS)

    missing: list[str] = []

    def add_missing(field_name: str) -> None:
        if field_name not in missing:
            missing.append(field_name)

    for field_name in REQUIRED_FIELDS:
        value = _get_value(
            deal,
            field_name,
        )

        if _is_empty(value):
            add_missing(field_name)

    quantity = _get_value(
        deal,
        "quantity",
    )

    if not _is_positive_number(quantity):
        add_missing("quantity")

    unit_price = _get_value(
        deal,
        "unit_price",
    )

    if not _is_positive_number(unit_price):
        add_missing("unit_price")

    return missing
