from __future__ import annotations

from collections.abc import Callable
from typing import Any

SkillHandler = Callable[..., Any]

class SkillNotFoundError(KeyError):
    """Вызывается, если запрошенный skill не зарегистрирован."""

class SkillsRegistry:
    """Реестр обработчиков skills для агентов."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillHandler] = {}

    def register(
        self,
        name: str,
        function: SkillHandler,
    ) -> None:
        """
        Регистрирует skill.

        Args:
            name: Уникальное имя skill.
            function: Функция-обработчик skill.
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "Имя skill должно быть непустой строкой"
            )

        if not callable(function):
            raise TypeError(
                f"Обработчик skill '{name}' должен быть вызываемым"
            )

        if name in self._skills:
            raise ValueError(
                f"Skill '{name}' уже зарегистрирован"
            )

        self._skills[name] = function

    def get(self, name: str) -> SkillHandler:
        """Возвращает обработчик skill по имени."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "Имя skill должно быть непустой строкой"
            )

        try:
            return self._skills[name]
        except KeyError as error:
            raise SkillNotFoundError(
                f"Skill '{name}' не найден"
            ) from error

    def has(self, name: str) -> bool:
        """Проверяет, зарегистрирован ли skill."""
        return name in self._skills

    def list_skills(self) -> list[str]:
        """Возвращает имена зарегистрированных skills."""
        return list(self._skills.keys())

    def list(self) -> list[str]:
        """
        Совместимость со старым API.

        Предпочтительно использовать list_skills().
        """
        return self.list_skills()
