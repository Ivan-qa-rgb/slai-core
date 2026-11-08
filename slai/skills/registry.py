from __future__ import annotations

from collections.abc import Callable
from typing import Any

from slai.tools.calculator import calculate_full_cost
from slai.tools.document_reader import read_document
from slai.tools.knowledge import find_relevant_rules

SkillHandler = Callable[[dict[str, Any]], dict[str, Any]]

class SkillNotFoundError(LookupError):
    """Вызывается, если skill не найден."""

class SkillsRegistry:
    """Реестр skills приложения."""

    def __init__(self) -> None:
        self._skills: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        handler: SkillHandler,
        *,
        title: str = "",
        description: str = "",
        input_schema: dict[str, str] | None = None,
    ) -> None:
        """Регистрирует skill."""

        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "Имя skill должно быть непустой строкой"
            )

        if not callable(handler):
            raise TypeError(
                f"Обработчик skill '{name}' должен быть вызываемым"
            )

        if name in self._skills:
            raise ValueError(
                f"Skill '{name}' уже зарегистрирован"
            )

        self._skills[name] = {
            "name": name,
            "title": title,
            "description": description,
            "handler": handler,
            "input": input_schema or {},
        }

    def has(self, name: str) -> bool:
        """Проверяет наличие skill."""
        return name in self._skills

    def get(self, name: str) -> dict[str, Any]:
        """Возвращает описание skill."""
        try:
            return self._skills[name]
        except KeyError as error:
            raise SkillNotFoundError(
                f"Skill '{name}' не найден"
            ) from error

    def list(self) -> list[dict[str, Any]]:
        """Возвращает список skills без внутренних обработчиков."""
        return [
            {
                "name": skill["name"],
                "title": skill["title"],
                "description": skill["description"],
                "input": dict(skill["input"]),
            }
            for skill in self._skills.values()
        ]

    def run(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Запускает skill по имени."""

        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "Имя skill должно быть непустой строкой"
            )

        if payload is None:
            payload = {}

        if not isinstance(payload, dict):
            raise TypeError(
                "Payload skill должен быть объектом"
            )

        skill = self.get(name)
        handler = skill["handler"]

        return handler(payload)

def run_cost_calculator(
    payload: dict[str, Any],
) -> dict[str, Any]:
    deal = payload.get("deal")

    if not isinstance(deal, dict):
        raise ValueError(
            "Поле 'deal' должно быть объектом"
        )

    result = calculate_full_cost(deal)

    return {
        "skill": "cost_calculator",
        "input": {
            "deal": deal,
        },
        "result": result,
        "source": "SLAI Calculator",
    }

def run_knowledge_search(
    payload: dict[str, Any],
) -> dict[str, Any]:
    query = payload.get("query")

    if not isinstance(query, str) or not query.strip():
        raise ValueError(
            "Поле 'query' обязательно и должно быть строкой"
        )

    query = query.strip()
    result = find_relevant_rules(query)

    return {
        "skill": "knowledge_search",
        "input": {
            "query": query,
        },
        "result": result,
        "source": "SLAI Knowledge Base",
    }

def run_document_extract(
    payload: dict[str, Any],
) -> dict[str, Any]:
    document = payload.get("document")

    if not isinstance(document, dict):
        raise ValueError(
            "Поле 'document' должно быть объектом"
        )

    result = read_document(document)

    return {
        "skill": "document_extract",
        "input": {
            "document": document,
        },
        "result": result,
        "source": "SLAI Document Reader",
    }

def create_default_registry() -> SkillsRegistry:
    """Создаёт реестр стандартных skills."""

    registry = SkillsRegistry()

    registry.register(
        name="cost_calculator",
        title="Расчёт себестоимости поставки",
        description=(
            "Считает полную стоимость, себестоимость "
            "и маржу сделки"
        ),
        handler=run_cost_calculator,
        input_schema={
            "deal": "object",
        },
    )

    registry.register(
        name="knowledge_search",
        title="Поиск по базе знаний",
        description=(
            "Ищет подходящие правила, регламенты "
            "и знания по запросу"
        ),
        handler=run_knowledge_search,
        input_schema={
            "query": "string",
        },
    )

    registry.register(
        name="document_extract",
        title="Чтение документа",
        description=(
            "Извлекает текст и данные "
            "из загруженного документа"
        ),
        handler=run_document_extract,
        input_schema={
            "document": "object",
        },
    )

    return registry

_DEFAULT_REGISTRY = create_default_registry()

def list_skills() -> list[dict[str, Any]]:
    """Совместимость со старым API."""
    return _DEFAULT_REGISTRY.list()

def run_skill(
    name: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Совместимость со старым API."""
    return _DEFAULT_REGISTRY.run(name, payload)
