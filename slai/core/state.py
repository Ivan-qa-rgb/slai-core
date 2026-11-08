from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict
import uuid

class Evidence(TypedDict, total=False):
    claim: str
    value: Any
    source: str
    page: int | None
    confidence: float
    agent: str

class DealState(TypedDict, total=False):
    run_id: str
    deal_id: int | str
    status: str
    created_at: str
    updated_at: str

    documents: list[dict[str, Any]]
    extracted_facts: dict[str, Any]
    rules: list[dict[str, Any]]

    calculation: dict[str, Any]
    customs_analysis: dict[str, Any]
    compliance_analysis: dict[str, Any]

    risks: list[dict[str, Any]]
    missing_information: list[str]
    recommendations: list[str]
    evidence: list[Evidence]

    audit: dict[str, Any]
    model_route: dict[str, str]

    retry_count: int
    current_node: str
    errors: list[str]
    events: list[dict[str, Any]]

def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()

def create_deal_state(
    deal_id: int | str,
    run_id: str | None = None,
) -> DealState:
    now = utc_now()

    return {
        "run_id": run_id or str(uuid.uuid4()),
        "deal_id": deal_id,
        "status": "created",
        "created_at": now,
        "updated_at": now,

        "documents": [],
        "extracted_facts": {},
        "rules": [],

        "calculation": {},
        "customs_analysis": {},
        "compliance_analysis": {},

        "risks": [],
        "missing_information": [],
        "recommendations": [],
        "evidence": [],

        "audit": {},
        "model_route": {},

        "retry_count": 0,
        "current_node": "start",
        "errors": [],
        "events": [],
    }

def create_initial_state(
    deal_id: int,
    run_id: str = "",
) -> DealState:
    now = utc_now()
    return {
        "run_id": str(run_id),
        "deal_id": int(deal_id),
        "status": "running",
        "current_node": "start",
        "completed_steps": [],
        "documents": [],
        "calculation": {},
        "audit": {},
        "errors": [],
        "events": [],
        "created_at": now,
        "updated_at": now,
    }

