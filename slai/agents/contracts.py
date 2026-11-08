from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class PaymentAgentResult:
    payment_status: str
    missing_information: list[str]
    risks: list[dict[str, Any]]
    sources: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentRequest:
    """Стандартизированный запрос к Worker Agent."""

    agent: str
    task: str
    context: dict[str, Any] = field(default_factory=dict)
    model: str | None = None
    prompt_version: str = "v1"

    def __post_init__(self) -> None:
        if not self.agent.strip():
            raise ValueError("agent не может быть пустым")

        if not self.task.strip():
            raise ValueError("task не может быть пустым")

        if not self.prompt_version.strip():
            raise ValueError(
                "prompt_version не может быть пустым"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentResponse:
    """Стандартизированный результат работы Worker Agent."""

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
            raise ValueError("agent не может быть пустым")

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


class PaymentAgent:
    name = "payment_agent"

    def run(
        self,
        deal_id: int,
        deal: dict[str, Any],
        documents: list[dict[str, Any]],
    ) -> AgentResponse:
        request = AgentRequest(
            agent=self.name,
            task="analyze_payment_documents",
            context={
                "deal_id": deal_id,
                "deal": deal,
                "documents": documents,
            },
        )

        try:
            payment_documents = [
                document
                for document in documents
                if document.get("document_type") == "payment"
            ]

            missing_information = []

            if not payment_documents:
                missing_information.append(
                    "Подтверждение оплаты депозита не предоставлено"
                )

            risks = []

            if missing_information:
                risks.append(
                    {
                        "title": "Риск предоплаты",
                        "description": (
                            "Отсутствует подтверждение оплаты депозита."
                        ),
                        "severity": "medium",
                        "source": "PAY-001",
                    }
                )

            result = PaymentAgentResult(
                payment_status=(
                    "confirmed"
                    if payment_documents
                    else "not_confirmed"
                ),
                missing_information=missing_information,
                risks=risks,
                sources=[
                    document.get("file_name", "")
                    for document in payment_documents
                ],
            )

            confidence = 0.9 if payment_documents else 0.8

            return AgentResponse(
                agent=self.name,
                status="completed",
                data=result.to_dict(),
                confidence=confidence,
                evidence=[
                    {
                        "type": "document",
                        "file_name": document.get("file_name", ""),
                        "document_type": document.get(
                            "document_type",
                            "",
                        ),
                    }
                    for document in payment_documents
                ],
                warnings=[],
                model=None,
                prompt_version=request.prompt_version,
                error=None,
            )

        except Exception as error:
            return AgentResponse(
                agent=self.name,
                status="failed",
                data={},
                confidence=0.0,
                evidence=[],
                warnings=[],
                requires_human_review=True,
                model=None,
                prompt_version=request.prompt_version,
                error=str(error),
            )