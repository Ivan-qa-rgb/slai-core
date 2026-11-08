from __future__ import annotations


from typing import Any


from core.agent_registry import (
    create_default_registry as create_core_registry,
)

from core.skills.consistency_checker import (
    check_consistency as core_check_consistency,
)

from core.skills.document_reader import (
    read_document as core_read_document,
)

from core.skills.field_extractor import (
    extract_fields as core_extract_fields,
)

from core.skills.missing_documents import (
    check_missing_documents as core_check_missing_documents,
)


from slai.skills.registry import (
    create_default_registry as create_slai_registry,
)

from slai.tools.calculator import (
    calculate_full_cost,
    calculate_supply_cost,
)

from slai.tools.document_reader import read_document

from slai.tools.knowledge import find_relevant_rules


from ...agents.payment_agent import PaymentAgent

from ...agents.supplier_agent import SupplierAgent

from .registry import UnifiedRegistry


def _get_document(
    payload: dict[str, Any],
) -> dict[str, Any]:
    document = payload.get("document")

    if not isinstance(document, dict):
        raise ValueError(
            "Поле 'document' должно быть объектом"
        )

    return document


def _get_documents(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    documents = payload.get("documents")

    if not isinstance(documents, list):
        raise ValueError(
            "Поле 'documents' должно быть массивом"
        )

    if not all(
        isinstance(document, dict)
        for document in documents
    ):
        raise ValueError(
            "Все элементы 'documents' должны быть объектами"
        )

    return documents


def run_core_read_document(
    payload: dict[str, Any],
) -> dict[str, Any]:
    return core_read_document(
        _get_document(payload)
    )


def run_core_extract_fields(
    payload: dict[str, Any],
) -> dict[str, Any]:
    return core_extract_fields(
        _get_document(payload)
    )


def run_core_check_consistency(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    return core_check_consistency(
        _get_documents(payload)
    )


def run_core_check_missing_documents(
    payload: dict[str, Any],
) -> list[dict[str, str]]:
    return core_check_missing_documents(
        _get_documents(payload)
    )


def run_calculate_supply_cost(
    payload: dict[str, Any],
) -> dict[str, Any]:
    deal = payload.get("deal")

    if deal is None:
        raise ValueError(
            "Поле 'deal' обязательно"
        )

    return calculate_supply_cost(deal)


def create_default_capabilities() -> UnifiedRegistry:
    registry = UnifiedRegistry()


    core_registry = create_core_registry()


    core_adapters = {
        "read_document": (
            run_core_read_document,
            {
                "document": "object",
            },
        ),
        "extract_fields": (
            run_core_extract_fields,
            {
                "document": "object",
            },
        ),
        "check_consistency": (
            run_core_check_consistency,
            {
                "documents": "array",
            },
        ),
        "check_missing_documents": (
            run_core_check_missing_documents,
            {
                "documents": "array",
            },
        ),
    }


    for skill_name in core_registry.skills.list_skills():
        handler, input_schema = core_adapters[skill_name]

        registry.register_skill(
            name=skill_name,
            handler=handler,
            title=f"Core skill: {skill_name}",
            description="Базовый skill агентного ядра",
            input_schema=input_schema,
        )


    for agent_info in core_registry.list_agents():
        agent = core_registry.get(agent_info["name"])

        registry.register_agent(agent)


    slai_registry = create_slai_registry()


    for skill_info in slai_registry.list():
        skill_name = skill_info["name"]
        skill = slai_registry.get(skill_name)

        registry.register_skill(
            name=skill_name,
            handler=skill["handler"],
            title=skill["title"],
            description=skill["description"],
            input_schema=skill["input"],
        )


    registry.register_tool(
        name="calculate_full_cost",
        handler=lambda payload: calculate_full_cost(
            payload.get("deal", {})
        ),
        description="Рассчитывает полную стоимость сделки",
    )


    registry.register_tool(
        name="calculate_supply_cost",
        handler=run_calculate_supply_cost,
        description="Рассчитывает стоимость поставки",
    )


    registry.register_tool(
        name="read_document",
        handler=lambda payload: read_document(
            payload.get("document", {})
        ),
        description="Читает и извлекает содержимое документа",
    )


    registry.register_tool(
        name="find_relevant_rules",
        handler=lambda payload: find_relevant_rules(
            payload.get("query", "")
        ),
        description="Ищет подходящие правила и знания",
    )


    registry.register_agent(PaymentAgent())

    registry.register_agent(SupplierAgent()) 
    return registry