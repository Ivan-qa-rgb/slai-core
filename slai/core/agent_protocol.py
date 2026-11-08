from __future__ import annotations



from dataclasses import asdict, dataclass, field
from typing import Any




@dataclass(slots=True)
class AgentRequest:
    agent: str
    task: str
    context: dict[str, Any] = field(default_factory=dict)
    model: str | None = None
    prompt_version: str = "v1"



    def __post_init__(self) -> None:
        if not self.agent.strip():
            raise ValueError(
                "agent не может быть пустым"
            )



        if not self.task.strip():
            raise ValueError(
                "task не может быть пустым"
            )



        if not self.prompt_version.strip():
            raise ValueError(
                "prompt_version не может быть пустым"
            )



    def to_dict(self) -> dict[str, Any]:
        return asdict(self)




@dataclass(slots=True)
class AgentResponse:
    agent: str
    status: str
    data: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    evidence: list[dict[str, Any]] = field(
        default_factory=list
    )
    warnings: list[str] = field(default_factory=list)
    requires_human_review: bool = False
    model: str | None = None
    prompt_version: str = "v1"
    error: str | None = None



    def __post_init__(self) -> None:
        allowed_statuses = {
            "completed",
            "failed",
            "needs_review",
        }



        if self.status not in allowed_statuses:
            raise ValueError(
                f"Недопустимый статус агента: {self.status}"
            )



        if not self.agent.strip():
            raise ValueError(
                "agent не может быть пустым"
            )



        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "confidence должен быть в диапазоне от 0 до 1"
            )



        if self.status == "failed" and not self.error:
            raise ValueError(
                "Для failed необходимо указать error"
            )



        if self.status == "needs_review":
            self.requires_human_review = True



    def to_dict(self) -> dict[str, Any]:
        return asdict(self)