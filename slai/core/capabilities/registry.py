from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .contracts import AgentSpec, Handler, SkillSpec, ToolSpec

class CapabilityNotFoundError(LookupError):
    """Возможность не найдена в UnifiedRegistry."""

class UnifiedRegistry:
    """Единый реестр агентов, skills и tools."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentSpec] = {}
        self._skills: dict[str, SkillSpec] = {}
        self._tools: dict[str, ToolSpec] = {}

    def register_skill(
        self,
        name: str,
        handler: Handler,
        *,
        title: str = "",
        description: str = "",
        input_schema: dict[str, str] | None = None,
        version: str = "1.0.0",
    ) -> SkillSpec:
        self._validate_name(name)

        if not callable(handler):
            raise TypeError(f"Обработчик skill '{name}' должен быть callable")

        if name in self._skills:
            raise ValueError(f"Skill '{name}' уже зарегистрирован")

        spec = SkillSpec(
            name=name,
            handler=handler,
            title=title,
            description=description,
            input_schema=input_schema or {},
            version=version,
        )

        self._skills[name] = spec
        return spec

    def register_tool(
        self,
        name: str,
        handler: Handler,
        *,
        description: str = "",
        version: str = "1.0.0",
        side_effects: bool = False,
        requires_approval: bool = False,
    ) -> ToolSpec:
        self._validate_name(name)

        if not callable(handler):
            raise TypeError(f"Обработчик tool '{name}' должен быть callable")

        if name in self._tools:
            raise ValueError(f"Tool '{name}' уже зарегистрирован")

        spec = ToolSpec(
            name=name,
            handler=handler,
            description=description,
            version=version,
            side_effects=side_effects,
            requires_approval=requires_approval,
        )

        self._tools[name] = spec
        return spec

    def register_agent(
        self,
        agent: Any,
        *,
        version: str = "1.0.0",
    ) -> AgentSpec:
        name = getattr(agent, "name", None)
        description = getattr(agent, "description", None)
        allowed_skills = getattr(agent, "allowed_skills", None)

        self._validate_name(name)

        if not isinstance(description, str):
            raise ValueError(
                f"Агент '{name}' должен иметь description"
            )

        if not isinstance(allowed_skills, (list, tuple, set)):
            raise ValueError(
                f"Агент '{name}' должен иметь allowed_skills"
            )

        if name in self._agents:
            raise ValueError(f"Агент '{name}' уже зарегистрирован")

        spec = AgentSpec(
            name=name,
            agent=agent,
            description=description,
            allowed_skills=tuple(allowed_skills),
            version=version,
        )

        self._agents[name] = spec
        return spec

    def get_skill(self, name: str) -> SkillSpec:
        try:
            return self._skills[name]
        except KeyError as error:
            raise CapabilityNotFoundError(
                f"Skill '{name}' не найден"
            ) from error

    def get_tool(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as error:
            raise CapabilityNotFoundError(
                f"Tool '{name}' не найден"
            ) from error

    def get_agent(self, name: str) -> Any:
        try:
            return self._agents[name].agent
        except KeyError as error:
            raise CapabilityNotFoundError(
                f"Агент '{name}' не найден"
            ) from error

    def run_skill(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        return self.get_skill(name).run(payload)

    def run_tool(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        return self.get_tool(name).run(payload)

    def list_skills(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "title": spec.title,
                "description": spec.description,
                "input": dict(spec.input_schema),
                "version": spec.version,
            }
            for spec in self._skills.values()
        ]

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "version": spec.version,
                "side_effects": spec.side_effects,
                "requires_approval": spec.requires_approval,
            }
            for spec in self._tools.values()
        ]

    def list_agents(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "skills": list(spec.allowed_skills),
                "version": spec.version,
            }
            for spec in self._agents.values()
        ]

    @staticmethod
    def _validate_name(name: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "Имя capability должно быть непустой строкой"
            )
