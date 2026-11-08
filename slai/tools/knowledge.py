from __future__ import annotations

import re
from typing import Any

KNOWLEDGE_BASE: list[dict[str, Any]] = [
    {
        "id": "LOG-001",
        "title": "Проверка базиса поставки",
        "keywords": [
            "exw",
            "fob",
            "cif",
            "базис",
            "перевозка",
            "логистика",
        ],
        "content": (
            "LOG-001. Проверь, кто организует перевозку, "
            "экспортное оформление и какие расходы несёт "
            "покупатель до передачи товара перевозчику."
        ),
        "source": "SLAI Internal Rule LOG-001",
        "status": "draft",
    },
    {
        "id": "PAY-001",
        "title": "Проверка перед депозитом",
        "keywords": [
            "депозит",
            "оплат",
            "предоплат",
            "аванс",
            "условия оплаты",
            "перед депозитом",
        ],
        "content": (
            "PAY-001. Перед подтверждением депозита проверь: "
            "юридические наименования сторон; согласованные товар, "
            "количество, цену и валюту; характеристики и комплектацию; "
            "условия поставки; сроки производства; размер депозита "
            "и условие оплаты остатка; порядок инспекции и требования "
            "к качеству; совпадение платёжных реквизитов."
        ),
        "source": "SLAI Internal Rule PAY-001",
        "status": "draft",
    },
    {
        "id": "DOC-001",
        "title": "Проверка документов сделки",
        "keywords": [
            "договор",
            "контракт",
            "спецификац",
            "инвойс",
            "документ",
            "качеств",
        ],
        "content": (
            "DOC-001. Проверь наличие договора, спецификации товара, "
            "инвойса, подтверждения оплаты и документов о качестве."
        ),
        "source": "SLAI Internal Rule DOC-001",
        "status": "draft",
    },
    {
        "id": "SHIP-001",
        "title": "Проверка готовности к отгрузке",
        "keywords": [
            "отгрузк",
            "готовност",
            "производств",
            "qc",
            "инспекц",
        ],
        "content": (
            "SHIP-001. Подтверди готовность товара, результаты "
            "контроля качества и соответствие отгрузки условиям договора."
        ),
        "source": "SLAI Internal Rule SHIP-001",
        "status": "draft",
    },
]

def _normalize_text(value: str) -> str:
    """Нормализует строку для поиска."""
    value = value.casefold().replace("ё", "е")
    value = re.sub(r"\s+", " ", value)
    return value.strip()

def _validate_knowledge_base() -> None:
    """Проверяет корректность записей базы знаний."""
    required_fields = {
        "id",
        "title",
        "keywords",
        "content",
        "source",
        "status",
    }

    for index, item in enumerate(KNOWLEDGE_BASE, start=1):
        if not isinstance(item, dict):
            raise TypeError(
                f"Запись базы знаний #{index} должна быть объектом"
            )

        missing_fields = required_fields - set(item)

        if missing_fields:
            raise ValueError(
                f"В записи базы знаний #{index} отсутствуют поля: "
                f"{', '.join(sorted(missing_fields))}"
            )

        if not isinstance(item["keywords"], list):
            raise TypeError(
                f"Поле keywords записи #{index} должно быть списком"
            )

def _calculate_match_score(
    query: str,
    keywords: list[str],
) -> int:
    """Возвращает количество совпавших ключевых слов."""
    score = 0

    for keyword in keywords:
        normalized_keyword = _normalize_text(keyword)

        if normalized_keyword and normalized_keyword in query:
            score += 1

    return score

def find_relevant_rules(
    query: str,
    *,
    limit: int | None = None,
    statuses: set[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Возвращает релевантные правила базы знаний.

    Результаты сортируются по количеству совпавших keywords.
    Внутренние записи базы не возвращаются напрямую.
    """
    if not isinstance(query, str):
        raise TypeError(
            "query должен быть строкой"
        )

    normalized_query = _normalize_text(query)

    if not normalized_query:
        return []

    if limit is not None:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError(
                "limit должен быть целым числом"
            )

        if limit <= 0:
            raise ValueError(
                "limit должен быть больше нуля"
            )

    if statuses is not None:
        if not isinstance(statuses, set):
            raise TypeError(
                "statuses должен быть множеством строк"
            )

        if not all(isinstance(status, str) for status in statuses):
            raise TypeError(
                "Все значения statuses должны быть строками"
            )

    _validate_knowledge_base()

    matched_rules: list[tuple[int, int, dict[str, Any]]] = []

    for index, item in enumerate(KNOWLEDGE_BASE):
        item_status = item["status"]

        if statuses is not None and item_status not in statuses:
            continue

        score = _calculate_match_score(
            normalized_query,
            item["keywords"],
        )

        if score > 0:
            matched_rules.append(
                (
                    score,
                    index,
                    {
                        **item,
                        "keywords": list(item["keywords"]),
                    },
                )
            )

    matched_rules.sort(
        key=lambda item: (-item[0], item[1])
    )

    results = [
        item
        for _, _, item in matched_rules
    ]

    if limit is not None:
        return results[:limit]

    return results

