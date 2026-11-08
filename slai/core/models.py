from __future__ import annotations



from dataclasses import asdict, dataclass
from typing import Any




@dataclass(slots=True)
class SupplierAgentResult:
    supplier_status: str
    risk_level: str
    company_verified: bool
    factory_verified: bool
    certificates: list[str]
    missing_information: list[str]
    risks: list[dict[str, Any]]
    next_actions: list[str]
    sources: list[str]



    def to_dict(self) -> dict[str, Any]:
        return asdict(self)