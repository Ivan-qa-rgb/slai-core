from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass(slots=True)
class AgentResult:
    """Стандартизированный результат работы агента."""

    agent: str
    status: str
    data: dict[str, Any] = field(default_factory=dict)
    sources: list[Any] = field(default_factory=list)
    errors: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Преобразует результат в обычный словарь."""
        return asdict(self)

class BaseAgent(ABC):
    """Базовый класс всех агентов SLAI."""

    name: str = "base_agent"
    description: str = "Базовый агент SLAI"
    allowed_skills: tuple[str, ...] = ()

    def __init__(self, skills_registry: Any) -> None:
        if skills_registry is None:
            raise ValueError(
                "skills_registry не может быть None"
            )

        self.skills = skills_registry

    @abstractmethod
    def run(self, context: dict[str, Any]) -> AgentResult:
        """
        Запускает агента.

        Каждый дочерний агент обязан реализовать этот метод.
        """
        raise NotImplementedError
