from __future__ import annotations

from typing import Any

MAX_DOCUMENT_TEXT_LENGTH = 5_000_000

def read_document(document: dict[str, Any]) -> dict[str, Any]:
    """
    Нормализует данные документа для дальнейшего анализа.

    Функция не открывает файл и не читает его с диска.
    Она работает с уже извлечённым текстом в поле
    'extracted_text'.
    """
    if not isinstance(document, dict):
        raise TypeError(
            "Документ должен быть объектом"
        )

    document_id = document.get("id")

    file_name = document.get("file_name")
    if file_name is not None and not isinstance(file_name, str):
        raise ValueError(
            "Поле 'file_name' должно быть строкой"
        )

    document_type = document.get("document_type")
    if document_type is not None and not isinstance(
        document_type,
        str,
    ):
        raise ValueError(
            "Поле 'document_type' должно быть строкой"
        )

    extracted_text = document.get("extracted_text", "")

    if extracted_text is None:
        extracted_text = ""

    if not isinstance(extracted_text, str):
        raise ValueError(
            "Поле 'extracted_text' должно быть строкой"
        )

    if len(extracted_text) > MAX_DOCUMENT_TEXT_LENGTH:
        raise ValueError(
            "Размер текста документа превышает допустимый лимит"
        )

    return {
        "document_id": document_id,
        "file_name": file_name,
        "document_type": document_type,
        "text": extracted_text,
    }
