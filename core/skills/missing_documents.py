from __future__ import annotations

import re
from typing import Any

Document = dict[str, Any]

def _normalize(value: Any) -> str:
    """Нормализует текст для поиска типа документа."""
    if not isinstance(value, str):
        return ""

    value = value.casefold().replace("ё", "е")
    return re.sub(r"\s+", " ", value).strip()

def _document_text(document: Document) -> str:
    """Объединяет тип документа и имя файла."""
    document_type = _normalize(document.get("document_type"))
    file_name = _normalize(document.get("file_name"))

    return f"{document_type} {file_name}".strip()

def _contains_any(
    value: str,
    keywords: tuple[str, ...],
) -> bool:
    return any(keyword in value for keyword in keywords)

def check_missing_documents(
    documents: list[Document],
) -> list[dict[str, str]]:
    """
    Проверяет наличие обязательных документов сделки.

    Проверка выполняется по:
    - document_type;
    - file_name.

    Функция не проверяет содержимое файлов.
    """
    if not isinstance(documents, list):
        raise TypeError(
            "Список документов должен быть массивом"
        )

    normalized_documents: list[str] = []

    for index, document in enumerate(documents, start=1):
        if not isinstance(document, dict):
            raise TypeError(
                f"Документ #{index} должен быть объектом"
            )

        normalized_documents.append(
            _document_text(document)
        )

    missing: list[dict[str, str]] = []

    has_contract = any(
        _contains_any(
            text,
            (
                "contract",
                "agreement",
                "договор",
                "соглашение",
            ),
        )
        for text in normalized_documents
    )

    if not has_contract:
        missing.append(
            {
                "code": "DOC-CONTRACT",
                "title": (
                    "Договор или подтверждение "
                    "условий сделки"
                ),
            }
        )

    has_specification = any(
        _contains_any(
            text,
            (
                "specification",
                "спецификац",
                "спец",
            ),
        )
        for text in normalized_documents
    )

    if not has_specification:
        missing.append(
            {
                "code": "DOC-SPECIFICATION",
                "title": "Спецификация товара",
            }
        )

    has_payment = any(
        _contains_any(
            text,
            (
                "payment",
                "deposit",
                "оплат",
                "платеж",
                "платёж",
                "депозит",
            ),
        )
        for text in normalized_documents
    )

    if not has_payment:
        missing.append(
            {
                "code": "DOC-PAYMENT",
                "title": "Подтверждение оплаты депозита",
            }
        )

    has_readiness = any(
        _contains_any(
            text,
            (
                "readiness",
                "ready_to_ship",
                "готовност",
                "отгруз",
            ),
        )
        for text in normalized_documents
    )

    if not has_readiness:
        missing.append(
            {
                "code": "DOC-READINESS",
                "title": (
                    "Подтверждение готовности товара "
                    "к отгрузке"
                ),
            }
        )

    has_quality = any(
        _contains_any(
            text,
            (
                "quality",
                "certificate",
                "conformity",
                "качеств",
                "сертификат",
                "соответств",
            ),
        )
        for text in normalized_documents
    )

    if not has_quality:
        missing.append(
            {
                "code": "DOC-QUALITY",
                "title": (
                    "Документы, подтверждающие качество "
                    "и соответствие товара"
                ),
            }
        )

    return missing
