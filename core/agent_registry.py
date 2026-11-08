from collections.abc import Callable
from typing import Any

from core.agents.documents_ai import DocumentsAI
from core.skills.consistency_checker import check_consistency
from core.skills.document_reader import read_document
from core.skills.field_extractor import extract_fields
from core.skills.missing_documents import check_missing_documents
from core.skills.registry import SkillsRegistry

class AgentNotFoundError(LookupError):
    """Вызывается, если агент не найден в реестре."""

class AgentRegistry:
    """Реестр зарегистрированных AI-агентов."""

    def __init__(self, skills_registry: SkillsRegistry) -> None:
        if skills_registry is None:
            raise ValueError("skills_registry не может быть None")

        self.skills = skills_registry
        self._agents: dict[str, Any] = {}

    def register(
        self,
        agent_class: Callable[[SkillsRegistry], Any],
    ) -> Any:
        """
        Создаёт и регистрирует агента.

        Класс агента должен принимать SkillsRegistry
        в конструкторе и содержать атрибуты:
        - name
        - description
        - allowed_skills
        """
        if not callable(agent_class):
            raise TypeError("agent_class должен быть вызываемым объектом")

        agent = agent_class(self.skills)

        name = getattr(agent, "name", None)
        description = getattr(agent, "description", None)
        allowed_skills = getattr(agent, "allowed_skills", None)

        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "У агента должно быть непустое строковое поле 'name'"
            )

        if not isinstance(description, str):
            raise ValueError(
                f"Агент '{name}' должен иметь строковое поле 'description'"
            )

        if isinstance(allowed_skills, str) or not isinstance(
            allowed_skills,
            (list, tuple, set),
        ):
            raise ValueError(
                f"Агент '{name}' должен иметь список 'allowed_skills'"
            )

        normalized_skills = list(allowed_skills)

        invalid_skills = [
            skill
            for skill in normalized_skills
            if not isinstance(skill, str) or not skill.strip()
        ]

        if invalid_skills:
            raise ValueError(
                f"Агент '{name}' содержит некорректные skills: "
                f"{invalid_skills!r}"
            )

        if name in self._agents:
            raise ValueError(
                f"Агент с именем '{name}' уже зарегистрирован"
            )

        self._agents[name] = agent
        return agent

    def get(self, name: str) -> Any:
        """Возвращает агента по имени."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Имя агента должно быть непустой строкой")

        try:
            return self._agents[name]
        except KeyError as error:
            raise AgentNotFoundError(
                f"Агент '{name}' не найден"
            ) from error

    def list_agents(self) -> list[dict[str, Any]]:
        """Возвращает информацию обо всех зарегистрированных агентах."""
        return [
            {
                "name": agent.name,
                "description": agent.description,
                "skills": list(agent.allowed_skills),
            }
            for agent in self._agents.values()
        ]

    def list(self) -> list[dict[str, Any]]:
        """
        Совместимость со старым API.

        Можно использовать registry.list(),
        но предпочтительный метод — registry.list_agents().
        """
        return self.list_agents()

def create_default_registry() -> AgentRegistry:
    """Создаёт реестр с базовыми skills и агентом документов."""
    skills = SkillsRegistry()

    skills.register("read_document", read_document)
    skills.register("extract_fields", extract_fields)
    skills.register("check_consistency", check_consistency)
    skills.register("check_missing_documents", check_missing_documents)

    registry = AgentRegistry(skills)
    registry.register(DocumentsAI)

    return registry
