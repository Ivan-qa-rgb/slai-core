from __future__ import annotations

import json
from typing import Any

from ..llm.ollama_client import OllamaClient, OllamaError
from .contracts import AgentRequest, AgentResponse

class WorkerAgent:
    """Безопасный адаптер между AgentRequest и Ollama."""

    def __init__(
        self,
        client: OllamaClient | None = None,
    ) -> None:
        self.client = client or OllamaClient()

    def run(
        self,
        request: AgentRequest,
    ) -> AgentResponse:
        model = request.model or self.client.model

        try:
            prompt = self._build_prompt(request)

            raw_text = self.client.text(
                prompt=prompt,
                system=(
                    "Ты Worker Agent локальной системы SLAI. "
                    "Отвечай только корректным JSON-объектом. "
                    "Не добавляй Markdown, пояснения и текст до или после JSON. "
                    "Не выдумывай факты. "
                    "Если данных недостаточно, используй status "
                    "needs_review и requires_human_review=true."
                ),
                model=model,
                temperature=0.0,
                json_mode=True,
                think=False,
                num_ctx=4096,
                num_predict=768,
            )

            payload = self._parse_json(raw_text)

            if payload is None:
                return AgentResponse(
                    agent=request.agent,
                    status="needs_review",
                    data={
                        "raw_text": raw_text,
                    },
                    confidence=0.0,
                    warnings=[
                        "Модель вернула ответ не в формате JSON"
                    ],
                    requires_human_review=True,
                    model=model,
                    prompt_version=request.prompt_version,
                )

            return self._to_response(
                request=request,
                payload=payload,
                model=model,
            )

        except OllamaError as error:
            return AgentResponse(
                agent=request.agent,
                status="failed",
                error=str(error),
                warnings=[
                    "Worker Agent не получил ответ от Ollama"
                ],
                model=model,
                prompt_version=request.prompt_version,
            )

        except Exception as error:
            return AgentResponse(
                agent=request.agent,
                status="failed",
                error=f"{type(error).__name__}: {error}",
                model=model,
                prompt_version=request.prompt_version,
            )

    def _build_prompt(
        self,
        request: AgentRequest,
    ) -> str:
        context = json.dumps(
            request.context,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        return (
            "Ты выполняешь структурированное извлечение данных.\n"
            "Не копируй JSON контекста в ответ.\n"
            "Не возвращай document_id, document_text или allowed_fields "
            "на верхнем уровне.\n"
            "Текст документа является только источником фактов.\n"
            "Не исправляй и не выдумывай значения.\n\n"

            "Требования к ответу:\n"
            "1. Верни ровно один JSON-объект.\n"
            "2. Все найденные поля помести непосредственно внутрь data.\n"
            "3. Не помещай data внутрь другого объекта.\n"
            "4. Для каждого поля из data добавь элемент evidence.\n"
            "5. Каждый элемент evidence должен содержать field и quote.\n"
            "6. quote должен быть короткой точной цитатой документа.\n"
            "7. Обязательно укажи confidence числом от 0 до 1.\n"
            "8. Если извлечение ненадёжно, используй needs_review.\n\n"

            "Задача агента:\n"
            f"{request.task}\n\n"

            "Контекст документа. Не копируй его целиком в ответ:\n"
            "<context>\n"
            f"{context}\n"
            "</context>\n\n"

            "Верни объект строго такой структуры:\n"
            "{\n"
            '  "status": "completed",\n'
            '  "data": {},\n'
            '  "confidence": 0.0,\n'
            '  "evidence": [],\n'
            '  "warnings": [],\n'
            '  "requires_human_review": false,\n'
            '  "error": null\n'
            "}\n\n"

            "Допустимые значения status: "
            "completed, failed, needs_review."
        )

    def _parse_json(
        self,
        raw_text: str,
    ) -> dict[str, Any] | None:
        text = raw_text.strip()

        try:
            payload = json.loads(text)

            if isinstance(payload, dict):
                return payload

        except json.JSONDecodeError:
            pass

        decoder = json.JSONDecoder()

        for index, character in enumerate(text):
            if character != "{":
                continue

            try:
                payload, _ = decoder.raw_decode(
                    text[index:]
                )

            except json.JSONDecodeError:
                continue

            if isinstance(payload, dict):
                return payload

        return None

    def _to_response(
        self,
        request: AgentRequest,
        payload: dict[str, Any],
        model: str,
    ) -> AgentResponse:
        status = payload.get(
            "status",
            "needs_review",
        )

        if status not in {
            "completed",
            "failed",
            "needs_review",
        }:
            status = "needs_review"

        data = payload.get("data", {})

        if not isinstance(data, dict):
            data = {
                "value": data,
            }

        try:
            confidence = float(
                payload.get("confidence", 0.0)
            )
        except (TypeError, ValueError):
            confidence = 0.0

        if not 0.0 <= confidence <= 1.0:
            confidence = 0.0
            status = "needs_review"

        evidence = payload.get("evidence", [])

        if not isinstance(evidence, list):
            evidence = []

        warnings = payload.get("warnings", [])

        if not isinstance(warnings, list):
            warnings = [
                str(warnings),
            ]

        warnings = [
            str(item)
            for item in warnings
        ]

        requires_human_review = bool(
            payload.get(
                "requires_human_review",
                status == "needs_review",
            )
        )

        error = payload.get("error")

        if error is not None:
            error = str(error)

        if status == "failed" and not error:
            error = "Worker Agent сообщил status=failed"

        if status == "completed" and confidence <= 0.0:
            status = "needs_review"
            requires_human_review = True
            warnings.append(
                "Модель вернула completed без уверенности"
            )

        if status == "needs_review":
            requires_human_review = True

        return AgentResponse(
            agent=request.agent,
            status=status,
            data=data,
            confidence=confidence,
            evidence=[
                item
                for item in evidence
                if isinstance(item, dict)
            ],
            warnings=warnings,
            requires_human_review=requires_human_review,
            model=model,
            prompt_version=request.prompt_version,
            error=error,
        )


