from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.base_agent import AgentResult, BaseAgent

class DocumentsAI(BaseAgent):
    """Агент анализа документов сделки."""

    name = "documents_ai"
    description = (
        "Анализирует документы сделки "
        "и проверяет их согласованность"
    )

    allowed_skills = (
        "read_document",
        "extract_fields",
        "check_consistency",
        "check_missing_documents",
    )

    def run(self, context: dict[str, Any]) -> AgentResult:
        """Анализирует переданные документы."""

        if not isinstance(context, dict):
            return AgentResult(
                agent=self.name,
                status="error",
                errors=[
                    "Контекст агента должен быть объектом"
                ],
            )

        documents = context.get("documents", [])

        if documents is None:
            documents = []

        if not isinstance(documents, list):
            return AgentResult(
                agent=self.name,
                status="error",
                errors=[
                    "Поле 'documents' должно быть массивом"
                ],
            )

        parsed_documents: list[dict[str, Any]] = []
        sources: list[str] = []
        errors: list[dict[str, Any]] = []

        for index, document in enumerate(documents):
            try:
                read_document = self._get_skill("read_document")
                extract_fields = self._get_skill("extract_fields")

                read_result = read_document(document)

                if not isinstance(read_result, dict):
                    raise TypeError(
                        "read_document должен вернуть объект"
                    )

                fields = extract_fields(read_result)

                parsed_document = {
                    **read_result,
                    "fields": fields,
                }

                parsed_documents.append(parsed_document)

                file_name = read_result.get("file_name")

                if not isinstance(file_name, str) or not file_name.strip():
                    file_name = f"document_{index + 1}"

                sources.append(file_name)

            except Exception as error:
                errors.append(
                    {
                        "document_index": index,
                        "error": str(error),
                    }
                )

        risks: Any = []
        missing_documents: Any = []

        if parsed_documents:
            try:
                check_consistency = self._get_skill(
                    "check_consistency"
                )
                risks = check_consistency(parsed_documents)
            except Exception as error:
                errors.append(
                    {
                        "step": "check_consistency",
                        "error": str(error),
                    }
                )

            try:
                check_missing_documents = self._get_skill(
                    "check_missing_documents"
                )
                missing_documents = check_missing_documents(
                    parsed_documents
                )
            except Exception as error:
                errors.append(
                    {
                        "step": "check_missing_documents",
                        "error": str(error),
                    }
                )

        if errors and parsed_documents:
            status = "partial"
        elif errors:
            status = "error"
        else:
            status = "ok"

        return AgentResult(
            agent=self.name,
            status=status,
            data={
                "documents": parsed_documents,
                "risks": risks,
                "missing_documents": missing_documents,
            },
            sources=sources,
            errors=errors,
        )

    def _get_skill(self, name: str) -> Callable[..., Any]:
        """Возвращает вызываемый обработчик skill."""

        skill = self.skills.get(name)

        if not callable(skill):
            raise TypeError(
                f"Skill '{name}' должен возвращать функцию"
            )

        return skill
