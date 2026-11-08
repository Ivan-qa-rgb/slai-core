from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

Handler = Callable[[dict[str, Any]], Any]

@dataclass(frozen=True)
class SkillSpec:
    name: str
    handler: Handler
    title: str = ""
    description: str = ""
    input_schema: dict[str, str] = field(default_factory=dict)
    version: str = "1.0.0"

    def run(self, payload: dict[str, Any] | None = None) -> Any:
        if payload is None:
            payload = {}

        if not isinstance(payload, dict):
            raise TypeError("Payload skill должен быть объектом")

        return self.handler(payload)

@dataclass(frozen=True)
class ToolSpec:
    name: str
    handler: Handler
    description: str = ""
    version: str = "1.0.0"
    side_effects: bool = False
    requires_approval: bool = False

    def run(self, payload: dict[str, Any] | None = None) -> Any:
        if payload is None:
            payload = {}

        if not isinstance(payload, dict):
            raise TypeError("Payload tool должен быть объектом")

        return self.handler(payload)

@dataclass(frozen=True)
class AgentSpec:
    name: str
    agent: Any
    description: str
    allowed_skills: tuple[str, ...]
    version: str = "1.0.0"
