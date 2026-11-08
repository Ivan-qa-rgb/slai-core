from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import AgentResponse

@dataclass(slots=True)
class PolicyDecision:
    accepted: bool
    status: str
    reasons: list[str] = field(default_factory=list)

def evaluate_response(
    response: AgentResponse,
    min_confidence: float = 0.70,
    require_data: bool = True,
) -> PolicyDecision:
    reasons: list[str] = []

    if response.status == "failed":
        return PolicyDecision(
            accepted=False,
            status="rejected",
            reasons=[
                response.error or "Агент завершился с ошибкой",
            ],
        )

    if response.status == "needs_review":
        reasons.append(
            "Агент запросил ручную проверку"
        )

    if response.requires_human_review:
        reasons.append(
            "Ответ требует подтверждения оператора"
        )

    if response.confidence < min_confidence:
        reasons.append(
            "Уверенность ниже установленного порога"
        )

    if require_data and not response.data:
        reasons.append(
            "Агент вернул пустое поле data"
        )

    if reasons:
        return PolicyDecision(
            accepted=False,
            status="needs_review",
            reasons=reasons,
        )

    return PolicyDecision(
        accepted=True,
        status="accepted",
        reasons=[],
    )
