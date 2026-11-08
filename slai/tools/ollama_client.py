from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from ..config import OLLAMA_MODEL, OLLAMA_URL
from ..workflow.audit_prompt import (
    AUDIT_RESPONSE_SCHEMA,
    AUDIT_SYSTEM_PROMPT,
    build_audit_prompt,
)

OLLAMA_TIMEOUT = int(
    os.getenv("OLLAMA_TIMEOUT", "600")
)

class OllamaClientError(RuntimeError):
    """Ошибка взаимодействия с Ollama."""

def _to_jsonable(value: Any) -> Any:
    """Преобразует объект в структуру, совместимую с JSON."""

    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            return None

        return value

    if isinstance(value, str):
        return value

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, Path):
        return str(value)

    if is_dataclass(value):
        return _to_jsonable(asdict(value))

    if isinstance(value, Mapping):
        return {
            str(key): _to_jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            _to_jsonable(item)
            for item in value
        ]

    if hasattr(value, "__dict__"):
        return _to_jsonable(vars(value))

    return str(value)

def _parse_model_json(content: Any) -> dict[str, Any]:
    """Преобразует ответ модели в словарь."""

    if not isinstance(content, str):
        raise OllamaClientError(
            "Ollama вернула содержимое не в виде строки"
        )

    normalized = content.strip()

    if not normalized:
        raise OllamaClientError(
            "Ollama вернула пустой ответ"
        )

    if normalized.startswith("```"):
        lines = normalized.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        normalized = "\n".join(lines).strip()

    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError as error:
        raise OllamaClientError(
            "Ollama вернула некорректный JSON"
        ) from error

    if not isinstance(parsed, dict):
        raise OllamaClientError(
            "Результат аудита должен быть JSON-объектом"
        )

    return parsed

def _validate_response_schema(
    response_schema: Any,
) -> str | dict[str, Any]:
    """Проверяет схему ответа Ollama."""

    if response_schema is None:
        return AUDIT_RESPONSE_SCHEMA

    if response_schema == "json":
        return "json"

    if isinstance(response_schema, dict):
        return response_schema

    raise TypeError(
        "response_schema должен быть 'json' "
        "или JSON-схемой в виде словаря"
    )

def request_audit(
    deal: Any,
    documents: list[dict[str, Any]],
    calculation: dict[str, Any],
    rules: list[dict[str, Any]],
    response_schema: str | dict[str, Any] | None = None,
    documents_ai: Any = None,
) -> dict[str, Any]:
    """
    Отправляет данные сделки в Ollama
    и возвращает структурированный аудит.
    """

    if not isinstance(documents, list):
        raise TypeError(
            "documents должен быть списком"
        )

    if not isinstance(calculation, dict):
        raise TypeError(
            "calculation должен быть объектом"
        )

    if not isinstance(rules, list):
        raise TypeError(
            "rules должен быть списком"
        )

    normalized_schema = _validate_response_schema(
        response_schema
    )

    prompt = build_audit_prompt(
        deal=deal,
        documents=documents,
        calculation=calculation,
        rules=rules,
        documents_ai=documents_ai,
    )

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": AUDIT_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "stream": False,
        "format": normalized_schema,
        "options": {
            "temperature": 0.1,
        },
    }

    request_body = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        url=OLLAMA_URL,
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=OLLAMA_TIMEOUT,
        ) as response:
            raw_response = response.read().decode(
                "utf-8",
                errors="replace",
            )

    except urllib.error.HTTPError as error:
        error_body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise OllamaClientError(
            f"Ollama вернула HTTP {error.code}: "
            f"{error_body[:1000]}"
        ) from error

    except urllib.error.URLError as error:
        raise OllamaClientError(
            "Не удалось подключиться к Ollama: "
            f"{error.reason}"
        ) from error

    except TimeoutError as error:
        raise OllamaClientError(
            "Истекло время ожидания ответа Ollama"
        ) from error

    try:
        response_data = json.loads(raw_response)
    except json.JSONDecodeError as error:
        raise OllamaClientError(
            "Ollama вернула некорректный JSON-ответ"
        ) from error

    if not isinstance(response_data, dict):
        raise OllamaClientError(
            "Ответ Ollama должен быть JSON-объектом"
        )

    message = response_data.get("message")

    if not isinstance(message, dict):
        raise OllamaClientError(
            "В ответе Ollama отсутствует поле message"
        )

    content = message.get("content")

    return _parse_model_json(content)
