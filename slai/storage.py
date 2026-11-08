from __future__ import annotations

import math
from typing import Any

from .db import get_connection


DEAL_FIELDS = (
    "supplier_name",
    "product_name",
    "quantity",
    "unit_price",
    "currency",
    "incoterm",
    "payment_terms",
    "production_days",
    "status",
)

TEXT_FIELDS = {
    "supplier_name",
    "product_name",
    "currency",
    "incoterm",
    "payment_terms",
    "status",
}

INTEGER_FIELDS = {
    "quantity",
    "production_days",
}

FLOAT_FIELDS = {
    "unit_price",
}


class DatabaseError(RuntimeError):
    """Базовая ошибка работы с базой данных."""


def _normalize_deal_id(deal_id: Any) -> int:
    if isinstance(deal_id, bool):
        raise ValueError("deal_id должен быть целым числом")

    if isinstance(deal_id, int):
        normalized_id = deal_id

    elif isinstance(deal_id, str) and deal_id.strip().isdigit():
        normalized_id = int(deal_id.strip())

    else:
        raise ValueError("deal_id должен быть целым числом")

    if normalized_id <= 0:
        raise ValueError("deal_id должен быть больше нуля")

    return normalized_id


def _validate_string(
    field: str,
    value: Any,
    *,
    required: bool = False,
) -> str | None:
    if value is None:
        if required:
            raise ValueError(f"{field} is required")

        return None

    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")

    normalized = value.strip()

    if required and not normalized:
        raise ValueError(f"{field} is required")

    return normalized


def _validate_number(
    field: str,
    value: Any,
) -> int | float | None:
    if value is None:
        return None

    if isinstance(value, bool):
        raise ValueError(f"{field} must be a number")

    if not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")

    numeric_value = float(value)

    if not math.isfinite(numeric_value):
        raise ValueError(f"{field} must be finite")

    if field in INTEGER_FIELDS:
        if not numeric_value.is_integer():
            raise ValueError(f"{field} must be an integer")

        integer_value = int(numeric_value)

        if integer_value < 0:
            raise ValueError(f"{field} cannot be negative")

        return integer_value

    if field in FLOAT_FIELDS:
        if numeric_value < 0:
            raise ValueError(f"{field} cannot be negative")

        return numeric_value

    return value


def _clean_deal(
    deal: dict[str, Any],
    *,
    partial: bool = False,
) -> dict[str, Any]:
    if not isinstance(deal, dict):
        raise ValueError("Deal must be an object")

    unknown_fields = set(deal) - set(DEAL_FIELDS)

    if unknown_fields:
        raise ValueError(
            "Unknown deal fields: "
            + ", ".join(sorted(unknown_fields))
        )

    cleaned: dict[str, Any] = {}

    for field, value in deal.items():
        if field in TEXT_FIELDS:
            cleaned[field] = _validate_string(
                field,
                value,
                required=(
                    field in {"supplier_name", "product_name"}
                    and not partial
                ),
            )

        elif field in INTEGER_FIELDS:
            cleaned[field] = _validate_number(field, value)

        elif field in FLOAT_FIELDS:
            cleaned[field] = _validate_number(field, value)

    if not partial:
        cleaned["supplier_name"] = _validate_string(
            "supplier_name",
            cleaned.get("supplier_name"),
            required=True,
        )

        cleaned["product_name"] = _validate_string(
            "product_name",
            cleaned.get("product_name"),
            required=True,
        )

    return cleaned


def _row_to_deal(row) -> dict[str, Any]:
    deal = dict(row)
    deal["id"] = int(deal["id"])

    if deal.get("quantity") is not None:
        deal["quantity"] = int(deal["quantity"])

    if deal.get("unit_price") is not None:
        deal["unit_price"] = float(deal["unit_price"])

    if deal.get("production_days") is not None:
        deal["production_days"] = int(deal["production_days"])

    return deal


def load_deals() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM deals
            ORDER BY id ASC
            """
        ).fetchall()

    return [_row_to_deal(row) for row in rows]


def get_deal(deal_id: int | str) -> dict[str, Any] | None:
    normalized_id = _normalize_deal_id(deal_id)

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM deals
            WHERE id = ?
            """,
            (normalized_id,),
        ).fetchone()

    if row is None:
        return None

    return _row_to_deal(row)


def add_deal(deal: dict[str, Any]) -> int:
    cleaned = _clean_deal(deal)

    if not cleaned:
        raise ValueError("Deal cannot be empty")

    fields = list(cleaned.keys())
    columns = ", ".join(fields)
    placeholders = ", ".join("?" for _ in fields)
    values = [cleaned[field] for field in fields]

    query = (
        f"INSERT INTO deals ({columns}) "
        f"VALUES ({placeholders})"
    )

    with get_connection() as connection:
        cursor = connection.execute(query, values)
        deal_id = cursor.lastrowid

    if deal_id is None:
        raise DatabaseError(
            "Не удалось получить ID созданной сделки"
        )

    return int(deal_id)


def update_deal(
    deal_id: int | str,
    deal: dict[str, Any],
) -> bool:
    normalized_id = _normalize_deal_id(deal_id)
    cleaned = _clean_deal(deal, partial=True)

    if not cleaned:
        return False

    assignments = ", ".join(
        f"{field} = ?"
        for field in cleaned
    )

    values = [cleaned[field] for field in cleaned]
    values.append(normalized_id)

    query = (
        f"UPDATE deals "
        f"SET {assignments} "
        "WHERE id = ?"
    )

    with get_connection() as connection:
        cursor = connection.execute(query, values)

    return cursor.rowcount > 0


def delete_deal(deal_id: int | str) -> bool:
    normalized_id = _normalize_deal_id(deal_id)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM deals
            WHERE id = ?
            """,
            (normalized_id,),
        )

    return cursor.rowcount > 0
