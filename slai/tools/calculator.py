from __future__ import annotations

import math
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

MONEY_FIELDS = (
    "unit_price",
    "logistics_cost",
    "customs_fee",
    "customs_cost",
    "brokerage_fee",
    "certification_cost",
    "other_costs",
)

RATE_FIELDS = (
    "duty_rate",
    "vat_rate",
)

def _get_value(
    deal: Any,
    field_name: str,
    default: Any = 0,
) -> Any:
    """Получает значение из словаря, объекта или dataclass."""
    if isinstance(deal, Mapping):
        return deal.get(field_name, default)

    return getattr(deal, field_name, default)

def _to_decimal(
    field_name: str,
    value: Any,
    *,
    default: Any = 0,
    allow_negative: bool = False,
) -> Decimal:
    """Преобразует значение в Decimal и проверяет его."""
    if value is None:
        value = default

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} должен быть числом"
        )

    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise ValueError(
            f"{field_name} должен быть числом"
        ) from error

    if not number.is_finite():
        raise ValueError(
            f"{field_name} должен быть конечным числом"
        )

    if not allow_negative and number < 0:
        raise ValueError(
            f"{field_name} не может быть отрицательным"
        )

    return number

def _get_quantity(deal: Any) -> int:
    """Получает и проверяет количество товара."""
    value = _get_value(deal, "quantity", 0)

    quantity = _to_decimal(
        "quantity",
        value,
    )

    if quantity != quantity.to_integral_value():
        raise ValueError(
            "quantity должно быть целым числом"
        )

    return int(quantity)

def _get_rate(
    deal: Any,
    field_name: str,
) -> Decimal:
    """Получает процентную ставку от 0 до 100."""
    rate = _to_decimal(
        field_name,
        _get_value(deal, field_name, 0),
    )

    if rate > 100:
        raise ValueError(
            f"{field_name} должно быть в диапазоне от 0 до 100"
        )

    return rate

def _get_customs_fee(deal: Any) -> Decimal:
    """
    Получает таможенный сбор.

    customs_fee — основное имя поля.
    customs_cost — устаревший совместимый алиас.
    """
    customs_fee = _get_value(
        deal,
        "customs_fee",
        None,
    )

    if customs_fee is None:
        customs_fee = _get_value(
            deal,
            "customs_cost",
            0,
        )

    return _to_decimal(
        "customs_fee",
        customs_fee,
    )

def _money(value: Decimal) -> float:
    """Преобразует Decimal в число для JSON-ответа."""
    return float(value)

def _calculate(deal: Any) -> dict[str, Any]:
    """Выполняет полный расчёт себестоимости."""
    if deal is None:
        raise ValueError(
            "deal не может быть None"
        )

    quantity = _get_quantity(deal)

    unit_price = _to_decimal(
        "unit_price",
        _get_value(deal, "unit_price", 0),
    )

    logistics_cost = _to_decimal(
        "logistics_cost",
        _get_value(deal, "logistics_cost", 0),
    )

    customs_fee = _get_customs_fee(deal)

    brokerage_fee = _to_decimal(
        "brokerage_fee",
        _get_value(deal, "brokerage_fee", 0),
    )

    certification_cost = _to_decimal(
        "certification_cost",
        _get_value(deal, "certification_cost", 0),
    )

    other_costs = _to_decimal(
        "other_costs",
        _get_value(deal, "other_costs", 0),
    )

    duty_rate = _get_rate(
        deal,
        "duty_rate",
    )

    vat_rate = _get_rate(
        deal,
        "vat_rate",
    )

    goods_cost = Decimal(quantity) * unit_price

    duty_cost = (
        goods_cost * duty_rate / Decimal("100")
    )

    # Упрощённая база НДС:
    # стоимость товара + пошлина + таможенный сбор.
    vat_base = (
        goods_cost
        + duty_cost
        + customs_fee
    )

    vat_cost = (
        vat_base * vat_rate / Decimal("100")
    )

    additional_costs = (
        logistics_cost
        + brokerage_fee
        + certification_cost
        + other_costs
    )

    total_cost = (
        goods_cost
        + duty_cost
        + vat_cost
        + customs_fee
        + additional_costs
    )

    if quantity > 0:
        unit_cost = total_cost / Decimal(quantity)
    else:
        unit_cost = Decimal("0")

    return {
        "quantity": quantity,
        "unit_price": _money(unit_price),
        "goods_cost": _money(goods_cost),
        "duty_rate": _money(duty_rate),
        "duty_cost": _money(duty_cost),
        "vat_rate": _money(vat_rate),
        "vat_base": _money(vat_base),
        "vat_cost": _money(vat_cost),
        "logistics_cost": _money(logistics_cost),
        "customs_fee": _money(customs_fee),
        "customs_cost": _money(customs_fee),
        "brokerage_fee": _money(brokerage_fee),
        "certification_cost": _money(
            certification_cost
        ),
        "other_costs": _money(other_costs),
        "additional_costs": _money(
            additional_costs
        ),
        "total_cost": _money(total_cost),
        "unit_cost": _money(unit_cost),
        "cost_per_unit": _money(unit_cost),
    }

def calculate_supply_cost(
    deal: Any,
) -> dict[str, Any]:
    """
    Рассчитывает себестоимость поставки.

    Сохраняет совместимость с прежними ключами:
    unit_cost, cost_per_unit, customs_cost.
    """
    result = _calculate(deal)

    return {
        "quantity": result["quantity"],
        "unit_price": result["unit_price"],
        "goods_cost": result["goods_cost"],
        "logistics_cost": result["logistics_cost"],
        "customs_cost": result["customs_cost"],
        "total_cost": result["total_cost"],
        "unit_cost": result["unit_cost"],
        "cost_per_unit": result["cost_per_unit"],
    }

def calculate_customs_cost(
    deal: Any,
) -> dict[str, Any]:
    """Рассчитывает таможенные платежи."""
    result = _calculate(deal)

    return {
        "quantity": result["quantity"],
        "unit_price": result["unit_price"],
        "goods_cost": result["goods_cost"],
        "duty_rate": result["duty_rate"],
        "duty_cost": result["duty_cost"],
        "vat_rate": result["vat_rate"],
        "vat_base": result["vat_base"],
        "vat_cost": result["vat_cost"],
        "customs_fee": result["customs_fee"],
        "customs_cost": result["customs_cost"],
        "total_customs_cost": _money(
            result["duty_cost"]
            + result["vat_cost"]
            + result["customs_fee"]
        ),
    }

def calculate_full_cost(
    deal: Any,
) -> dict[str, Any]:
    """Рассчитывает полную стоимость сделки."""
    return _calculate(deal)
