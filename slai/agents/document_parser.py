from __future__ import annotations

import re

from typing import Any

from ..llm.ollama_client import OllamaClient
from .contracts import AgentRequest, AgentResponse
from .worker import WorkerAgent

class DocumentParserAgent:
    """Агент извлечения структурированных данных из документа."""

    ALLOWED_FIELDS = {
        "supplier",
        "country",
        "invoice_number",
        "invoice_date",
        "currency",
        "items",
        "total_amount",
    }

    def __init__(
        self,
        worker: WorkerAgent | None = None,
        model: str = "qwen3:4b",
    ) -> None:
        self.model = model
        self.worker = worker or WorkerAgent(
            client=OllamaClient(
                model=model,
                timeout=300.0,
                think=False,
                num_ctx=4096,
                num_predict=768,
            )
        )

    def run(
        self,
        document_id: int | str,
        document_text: str,
        document_name: str | None = None,
    ) -> AgentResponse:
        if not document_text.strip():
            return AgentResponse(
                agent="document_parser",
                status="needs_review",
                data={},
                confidence=0.0,
                warnings=[
                    "Текст документа отсутствует"
                ],
                requires_human_review=True,
                prompt_version="document-parser-v1",
            )

        request = AgentRequest(
            agent="document_parser",
            task=(
                "Извлеки из документа реквизиты. "
                "Не выдумывай значения. "
                "Если поле отсутствует, не заполняй его. "
                "В data разрешены только поля: "
                "supplier, country, invoice_number, "
                "invoice_date, currency, items, total_amount. "
                "Для каждого найденного поля добавь evidence "
                "с короткой цитатой из документа."
            ),
            context={
                "document_id": document_id,
                "document_name": document_name,
                "document_text": document_text,
                "allowed_fields": sorted(
                    self.ALLOWED_FIELDS
                ),
            },
            model=self.model,
            prompt_version="document-parser-v1",
        )

        response = self.worker.run(request)

        if response.status == "failed":
            return response

        source_data = response.data
        normalized_data: dict[str, Any] = {}
        warnings = list(response.warnings)

        for field_name in self.ALLOWED_FIELDS:
            if field_name not in source_data:
                continue

            value = source_data[field_name]

            if value is None:
                continue

            if field_name == "items":
                if not isinstance(value, list):
                    warnings.append(
                        "Поле items имеет неправильный формат"
                    )
                    continue

            normalized_data[field_name] = value

        unknown_fields = sorted(
            set(source_data) - self.ALLOWED_FIELDS
        )

        if unknown_fields:
            warnings.append(
                "Удалены неизвестные поля: "
                + ", ".join(unknown_fields)
            )

        validation_warnings: list[str] = []
        normalized_evidence: list[dict[str, Any]] = []
        evidence_by_field: dict[str, str] = {}

        raw_evidence = response.evidence

        if not isinstance(raw_evidence, list):
            raw_evidence = []

        for item in raw_evidence:
            if not isinstance(item, dict):
                validation_warnings.append(
                    "Элемент evidence имеет неправильный формат"
                )
                continue

            field_name = item.get("field")
            quote = item.get("quote")

            if quote is None:
                quote = item.get("evidence")

            if not isinstance(field_name, str):
                validation_warnings.append(
                    "В evidence отсутствует корректное поле field"
                )
                continue

            if not isinstance(quote, str) or not quote.strip():
                validation_warnings.append(
                    f"Для поля {field_name} отсутствует quote"
                )
                continue

            field_name = field_name.strip()
            quote = quote.strip()

            if field_name in evidence_by_field:
                continue

            evidence_by_field[field_name] = quote
            normalized_evidence.append(
                {
                    "field": field_name,
                    "quote": quote,
                }
            )

            if quote not in document_text:
                validation_warnings.append(
                    f"Цитата для поля {field_name} "
                    "отсутствует в исходном документе"
                )

        for field_name in normalized_data:
            if field_name not in evidence_by_field:
                validation_warnings.append(
                    f"Для поля {field_name} отсутствует evidence"
                )

        expected_patterns = {
            "invoice_number": (
                r"ИНВОЙС\s*№\s*"
                r"([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)"
            ),
            "invoice_date": (
                r"(?:Дата|Date)\s*:\s*"
                r"(\d{4}-\d{2}-\d{2})"
            ),
            "currency": (
                r"(?:Валюта|Currency)\s*:\s*"
                r"([A-Z]{3})"
            ),
            "total_amount": (
                r"(?:Общая сумма|Total amount)\s*:\s*"
                r"([0-9]+(?:[.,][0-9]+)?)"
            ),
        }

        canonical_values: dict[str, str] = {}

        for field_name, pattern in expected_patterns.items():
            match = re.search(
                pattern,
                document_text,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            expected_value = match.group(1).strip()

            if field_name == "total_amount":
                expected_value = expected_value.replace(
                    ",",
                    ".",
                )

            canonical_values[field_name] = expected_value

            if field_name not in normalized_data:
                continue

            actual_value = str(
                normalized_data[field_name]
            ).strip()

            comparable_actual = actual_value

            if field_name == "total_amount":
                comparable_actual = comparable_actual.replace(
                    ",",
                    ".",
                )

            if comparable_actual != expected_value:
                warnings.append(
                    f"Поле {field_name} было нормализовано "
                    f"по исходному документу: "
                    f"{actual_value!r} -> {expected_value!r}"
                )

                normalized_data[field_name] = expected_value

        source_label_patterns = {
            "invoice_number": (
                r"С\s*\s*"
                r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*"
            ),
            "supplier": (
                r"оставщик\s*:\s*"
                r"[^\n.!?]+"
            ),
            "country": (
                r"Страна\s+происхождения\s*:\s*"
                r"[^\n.!?]+"
            ),
            "invoice_date": (
                r"(?:ата|Date)\s*:\s*"
                r"\d{4}-\d{2}-\d{2}"
            ),
            "currency": (
                r"(?:алюта|Currency)\s*:\s*"
                r"[A-Z]{3}"
            ),
            "total_amount": (
                r"(?:бщая сумма|Total amount)\s*:\s*"
                r"[0-9]+(?:[.,][0-9]+)?"
            ),
        }

        for field_name in normalized_data:
            pattern = source_label_patterns.get(
                field_name
            )

            if pattern is None:
                continue

            if not re.search(
                pattern,
                document_text,
                flags=re.IGNORECASE,
            ):
                validation_warnings.append(
                    f"оле {field_name} не подтверждено "
                    "корректной меткой в исходном документе"
                )

            quote = evidence_by_field.get(field_name)

            if quote and not re.search(
                pattern,
                quote,
                flags=re.IGNORECASE,
            ):
                validation_warnings.append(
                    f"Цитата для поля {field_name} "
                    "не содержит корректную метку поля"
                )

        for field_name, value in normalized_data.items():
            if field_name == "items":
                continue

            quote = evidence_by_field.get(field_name)

            if not quote:
                continue

            if quote not in document_text:
                continue

            if field_name in canonical_values:
                continue

            value_text = str(value).strip()

            if value_text not in quote:
                validation_warnings.append(
                    f"Значение поля {field_name} "
                    "отсутствует в его цитате"
                )

        if "invoice_date" in normalized_data:
            value = str(
                normalized_data["invoice_date"]
            ).strip()

            if not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}",
                value,
            ):
                validation_warnings.append(
                    "invoice_date имеет формат, отличный "
                    "от YYYY-MM-DD"
                )

        if "invoice_date" in normalized_data:
            value = str(
                normalized_data["invoice_date"]
            ).strip()

            if not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}",
                value,
            ):
                validation_warnings.append(
                    "invoice_date имеет формат, отличный "
                    "от YYYY-MM-DD"
                )

        status = response.status
        requires_human_review = (
            response.requires_human_review
        )
        confidence = response.confidence

        if not normalized_data:
            status = "needs_review"
            requires_human_review = True
            warnings.append(
                "Не удалось извлечь разрешённые поля"
            )

        if confidence <= 0.0:
            status = "needs_review"
            requires_human_review = True
            warnings.append(
                "У результата отсутствует уверенность"
            )

        if validation_warnings:
            status = "needs_review"
            requires_human_review = True
            confidence = 0.0
            warnings.extend(validation_warnings)

        return AgentResponse(
            agent="document_parser",
            status=status,
            data=normalized_data,
            confidence=confidence,
            evidence=normalized_evidence,
            warnings=warnings,
            requires_human_review=requires_human_review,
            model=response.model,
            prompt_version="document-parser-v1",
            error=response.error,
        )
