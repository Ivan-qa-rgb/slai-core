from __future__ import annotations

import re
from typing import Any

QUANTITY_PATTERN = re.compile(
    r"(?P<value>\d[\d\s\u00A0]*)\s*"
    r"(?:штук|шт\.|pieces|pcs)"
    r"(?=\s|$|[^\w])",
    re.IGNORECASE,
)

CURRENCY_CNY_PATTERN = re.compile(
    r"\bCNY\b|юан",
    re.IGNORECASE,
)

CURRENCY_USD_PATTERN = re.compile(
    r"\bUSD\b|долл",
    re.IGNORECASE,
)

PRODUCT_PATTERN = re.compile(
    r"(?:^|\r?\n)\s*"
    r"(?:Товар|Product|Goods)"
    r"\s*:\s*(?P<value>[^\r\n]+)",
    re.IGNORECASE,
)

DEPOSIT_PATTERN = re.compile(
    r"(?:"
    r"^\s*Deposit\s*:\s*"
    r"|"
    r"(?P<payment_prefix>\d{1,3})\s*%\s*"
    r"(?:deposit|аванс|депозит)"
    r")"
    r"(?P<value>\d{1,3})?\s*%",
    re.IGNORECASE | re.MULTILINE,
)

DEPOSIT_PERCENT_PATTERN = re.compile(
    r"(?:"
    r"^\s*Deposit\s*:\s*"
    r"|"
    r"(?<!\d)"
    r")"
    r"(?P<value>\d{1,3})\s*%"
    r"(?:\s*=\s*[\d\s\u00A0.,]+)?"
    r"(?:\s|$|,)",
    re.IGNORECASE | re.MULTILINE,
)

BALANCE_PERCENT_PATTERN = re.compile(
    r"(?:"
    r"^\s*Balance\s*:\s*"
    r"|"
    r"(?<!\d)"
    r")"
    r"(?P<value>\d{1,3})\s*%"
    r"(?:\s*before\s+shipment|\s*баланс|\s*остаток|\s*перед\s+отгрузкой)",
    re.IGNORECASE | re.MULTILINE,
)

PAYMENT_TERMS_PATTERN = re.compile(
    r"(?:^|\r?\n)\s*"
    r"(?:Payment terms|Условия оплаты)"
    r"\s*:\s*(?P<value>[^\r\n]+)",
    re.IGNORECASE,
)

UNIT_PRICE_PATTERN = re.compile(
    r"(?:^|\r?\n)\s*"
    r"Unit price\s*:\s*"
    r"(?P<value>[\d\s\u00A0.,]+)\s*"
    r"(?P<currency>CNY|USD)\b",
    re.IGNORECASE,
)

TOTAL_AMOUNT_PATTERN = re.compile(
    r"(?:^|\r?\n)\s*"
    r"(?:Total contract amount|Total amount|Contract amount)"
    r"\s*:\s*"
    r"(?P<value>[\d\s\u00A0.,]+)\s*"
    r"(?P<currency>CNY|USD)\b",
    re.IGNORECASE,
)

PAYMENT_DATE_PATTERN = re.compile(
    r"(?:^|\r?\n)\s*"
    r"(?:Payment date|Дата оплаты)"
    r"\s*:\s*"
    r"(?P<value>\d{4}-\d{2}-\d{2}|"
    r"\d{2}[./]\d{2}[./]\d{4})",
    re.IGNORECASE,
)

SHIPMENT_DATE_PATTERN = re.compile(
    r"(?:^|\r?\n)\s*"
    r"(?:Shipment date|Shipping date|Дата отгрузки)"
    r"\s*:\s*"
    r"(?P<value>\d{4}-\d{2}-\d{2}|"
    r"\d{2}[./]\d{2}[./]\d{4})",
    re.IGNORECASE,
)

INCOTERM_PATTERN = re.compile(
    r"(?:^|\r?\n)\s*"
    r"(?:Delivery terms|Incoterms|Условия поставки)"
    r"\s*:\s*(?P<value>[^\r\n]+)",
    re.IGNORECASE,
)

def _parse_integer(value: str) -> int:
    """Преобразует число с обычными или неразрывными пробелами."""
    normalized = re.sub(r"[\s\u00A0]", "", value)

    if not normalized.isdigit():
        raise ValueError(
            f"Некорректное целое число: {value!r}"
        )

    return int(normalized)

def _parse_amount(value: str) -> int | float:
    """Преобразует денежное значение в число."""
    normalized = re.sub(r"[\s\u00A0]", "", value)
    normalized = normalized.replace(",", ".")

    amount = float(normalized)

    if amount.is_integer():
        return int(amount)

    return amount

def _extract_percent(
    pattern: re.Pattern[str],
    text: str,
) -> int | None:
    match = pattern.search(text)

    if not match:
        return None

    value = match.group("value")
    percent = int(value)

    if 0 <= percent <= 100:
        return percent

    return None

def extract_fields(
    document: dict[str, Any],
) -> dict[str, Any]:
    """
    Извлекает структурированные поля из текста документа.

    Поля:
    - quantity;
    - currency;
    - product;
    - unit_price;
    - total_amount;
    - deposit_percent;
    - balance_percent;
    - payment_terms;
    - deposit_payment_date;
    - shipment_date;
    - incoterm.
    """
    if not isinstance(document, dict):
        raise TypeError(
            "Документ должен быть объектом"
        )

    text = document.get("text", "")

    if text is None:
        text = ""

    if not isinstance(text, str):
        raise ValueError(
            "Поле 'text' должно быть строкой"
        )

    fields: dict[str, Any] = {}

    quantity_match = QUANTITY_PATTERN.search(text)

    if quantity_match:
        fields["quantity"] = _parse_integer(
            quantity_match.group("value")
        )

    if CURRENCY_CNY_PATTERN.search(text):
        fields["currency"] = "CNY"
    elif CURRENCY_USD_PATTERN.search(text):
        fields["currency"] = "USD"

    product_match = PRODUCT_PATTERN.search(text)

    if product_match:
        product = product_match.group("value").strip()

        if product:
            fields["product"] = product

    unit_price_match = UNIT_PRICE_PATTERN.search(text)

    if unit_price_match:
        fields["unit_price"] = _parse_amount(
            unit_price_match.group("value")
        )

    total_amount_match = TOTAL_AMOUNT_PATTERN.search(text)

    if total_amount_match:
        fields["total_amount"] = _parse_amount(
            total_amount_match.group("value")
        )

    deposit_percent = _extract_percent(
        DEPOSIT_PERCENT_PATTERN,
        text,
    )

    if deposit_percent is not None:
        fields["deposit_percent"] = deposit_percent

    balance_percent = _extract_percent(
        BALANCE_PERCENT_PATTERN,
        text,
    )

    if balance_percent is not None:
        fields["balance_percent"] = balance_percent

    payment_terms_match = PAYMENT_TERMS_PATTERN.search(text)

    if payment_terms_match:
        fields["payment_terms"] = (
            payment_terms_match.group("value").strip()
        )
    else:
        payment_parts = []

        if deposit_percent is not None:
            payment_parts.append(
                f"{deposit_percent}% deposit"
            )

        if balance_percent is not None:
            payment_parts.append(
                f"{balance_percent}% before shipment"
            )

        if payment_parts:
            fields["payment_terms"] = ", ".join(
                payment_parts
            )

    payment_date_match = PAYMENT_DATE_PATTERN.search(text)

    if payment_date_match:
        fields["deposit_payment_date"] = (
            payment_date_match.group("value")
        )

    shipment_date_match = SHIPMENT_DATE_PATTERN.search(text)

    if shipment_date_match:
        fields["shipment_date"] = (
            shipment_date_match.group("value")
        )

    incoterm_match = INCOTERM_PATTERN.search(text)

    if incoterm_match:
        fields["incoterm"] = (
            incoterm_match.group("value").strip()
        )

    return fields
