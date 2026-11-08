from ..db import get_connection
from ..models import WorkflowResult
from ..validators import validate_deal



from slai.core.capabilities import get_capabilities



from ..tools.ollama_client import request_audit



from ..workflow.validate_audit import (
    validate_audit,
    prioritize_missing_items,
)



from ..workflow.normalize_audit import normalize_audit



from ..workflow.audit_prompt import AUDIT_RESPONSE_SCHEMA




class WorkflowValidationError(Exception):
    pass




def validate_input_step(context):
    missing = validate_deal(context["deal"])



    if missing:
        context["result"].status = "missing_data"
        context["result"].missing_fields = missing



        raise WorkflowValidationError(
            "missing fields: "
            + ", ".join(missing)
        )




def load_deal_documents(deal_id):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                file_name,
                document_type,
                extracted_text
            FROM documents
            WHERE deal_id = ?
              AND file_name NOT LIKE 'test_%'
            ORDER BY id
            """,
            (deal_id,),
        ).fetchall()



    return [
        {
            "file_name": row["file_name"],
            "document_type": row["document_type"],
            "content": row["extracted_text"] or "",
        }
        for row in rows
    ]


def read_documents_step(context):
    documents = context["documents"]



    if not documents:
        documents = load_deal_documents(
            context["deal"].id
        )



    else:
        documents = [
            {
                "file_name": document.get(
                    "file_name",
                    "",
                ),
                "document_type": document.get(
                    "document_type",
                    "",
                ),
                "content": (
                    document.get("content")
                    or document.get("extracted_text")
                    or ""
                ),
            }
            for document in documents
        ]



    context["documents"] = documents



    context["result"].documents = [
        {
            "file_name": document.get(
                "file_name",
                "",
            ),
            "document_type": document.get(
                "document_type",
                "",
            ),
            "content_length": len(
                document.get("content", "")
            ),
        }
        for document in documents
        if isinstance(document, dict)
    ]




def supplier_check_step(context):
    registry = get_capabilities()



    agent = registry.get_agent("supplier_agent")



    if agent is None:
        raise RuntimeError(
            "supplier_agent agent is not registered"
        )



    documents = [
        {
            "file_name": document.get(
                "file_name",
                "",
            ),
            "document_type": document.get(
                "document_type",
                "",
            ),
            "extracted_text": (
                document.get("content")
                or document.get("extracted_text")
                or ""
            ),
        }
        for document in context["documents"]
    ]



    deal = context["deal"]



    agent_result = agent.run(
        deal.id,
        {
            "supplier_name": deal.supplier_name,
        },
        documents,
    )



    context["supplier_agent"] = agent_result




def documents_ai_step(context):
    registry = get_capabilities()



    agent = registry.get_agent("documents_ai")



    if agent is None:
        raise RuntimeError(
            "documents_ai agent is not registered"
        )



    documents = [
        {
            "id": None,
            "file_name": document.get(
                "file_name",
                "",
            ),
            "document_type": document.get(
                "document_type",
                "",
            ),
            "extracted_text": (
                document.get("content")
                or document.get("extracted_text")
                or ""
            ),
        }
        for document in context["documents"]
    ]



    agent_result = agent.run(
        {
            "deal_id": context["deal"].id,
            "documents": documents,
        }
    )



    context["documents_ai"] = agent_result




def payment_agent_step(context):
    registry = get_capabilities()



    agent = registry.get_agent("payment_agent")



    if agent is None:
        raise RuntimeError(
            "payment_agent agent is not registered"
        )



    documents = [
        {
            "file_name": document.get(
                "file_name",
                "",
            ),
            "document_type": document.get(
                "document_type",
                "",
            ),
            "extracted_text": (
                document.get("content")
                or document.get("extracted_text")
                or ""
            ),
        }
        for document in context["documents"]
    ]



    deal = context["deal"]



    agent_result = agent.run(
        deal.id,
        {
            "supplier_name": deal.supplier_name,
            "payment_terms": deal.payment_terms,
        },
        documents,
    )



    context["payment_agent"] = agent_result




def find_rules_step(context):
    deal = context["deal"]



    query = " ".join(
        [
            deal.incoterm or "",
            deal.payment_terms or "",
            "депозит",
            "оплата",
            "документы",
            "отгрузка",
        ]
    )



    registry = get_capabilities()



    context["rules"] = registry.run_tool(
        "find_relevant_rules",
        {
            "query": query,
        },
    )




def calculate_step(context):
    registry = get_capabilities()



    context["result"].calculation = registry.run_tool(
        "calculate_supply_cost",
        {
            "deal": context["deal"],
        },
    )




def audit_step(context):
    documents_ai_result = context.get("documents_ai")
    payment_agent_result = context.get("payment_agent")
    supplier_agent_result = context.get("supplier_agent")




    documents_ai = None
    documents_ai_data = {}
    documents_ai_sources = []



    if documents_ai_result:
        data = getattr(
            documents_ai_result,
            "data",
            {},
        )



        sources = getattr(
            documents_ai_result,
            "sources",
            [],
        )



        if isinstance(data, dict):
            documents_ai_data = data



        if isinstance(sources, list):
            documents_ai_sources = sources



        documents_ai = {
            "data": documents_ai_data,
            "sources": documents_ai_sources,
        }




    payment_agent = None
    payment_agent_data = {}
    payment_agent_evidence = []



    if payment_agent_result:
        data = getattr(
            payment_agent_result,
            "data",
            {},
        )



        evidence = getattr(
            payment_agent_result,
            "evidence",
            [],
        )



        if isinstance(data, dict):
            payment_agent_data = data



        if isinstance(evidence, list):
            payment_agent_evidence = evidence



        payment_agent = {
            "data": payment_agent_data,
            "evidence": payment_agent_evidence,
        }




    supplier_agent = None
    supplier_agent_data = {}
    supplier_agent_evidence = []



    if supplier_agent_result:
        data = getattr(
            supplier_agent_result,
            "data",
            {},
        )



        evidence = getattr(
            supplier_agent_result,
            "evidence",
            [],
        )



        if isinstance(data, dict):
            supplier_agent_data = data



        if isinstance(evidence, list):
            supplier_agent_evidence = evidence



        supplier_agent = {
            "data": supplier_agent_data,
            "evidence": supplier_agent_evidence,
        }




    audit = request_audit(
        deal=context["deal"],
        documents=context["documents"],
        calculation=context["result"].calculation,
        rules=context["rules"],
        response_schema=AUDIT_RESPONSE_SCHEMA,
        documents_ai=documents_ai,
    )




    audit = prioritize_missing_items(audit)
    audit = normalize_audit(audit)



    errors = validate_audit(audit)



    if errors:
        raise WorkflowValidationError(
            "; ".join(errors)
        )




    if documents_ai_result:
        risks = documents_ai_data.get(
            "risks",
            [],
        )



        missing_documents = documents_ai_data.get(
            "missing_documents",
            [],
        )



        audit["documents_ai"] = {
            "risks": (
                risks[:20]
                if isinstance(risks, list)
                else []
            ),
            "missing_documents": (
                missing_documents[:20]
                if isinstance(
                    missing_documents,
                    list,
                )
                else []
            ),
            "sources": documents_ai_sources[:20],
        }




    if payment_agent_result:
        payment_status = payment_agent_data.get(
            "payment_status",
            "not_confirmed",
        )



        missing_information = payment_agent_data.get(
            "missing_information",
            [],
        )



        payment_risks = payment_agent_data.get(
            "risks",
            [],
        )



        audit["payment_agent"] = {
            "payment_status": payment_status,
            "missing_information": (
                missing_information[:20]
                if isinstance(
                    missing_information,
                    list,
                )
                else []
            ),
            "risks": (
                payment_risks[:20]
                if isinstance(
                    payment_risks,
                    list,
                )
                else []
            ),
            "evidence": payment_agent_evidence[:20],
        }




    if supplier_agent_result:
        supplier_status = supplier_agent_data.get(
            "supplier_status",
            "needs_review",
        )



        supplier_risk_level = supplier_agent_data.get(
            "risk_level",
            "medium",
        )



        supplier_missing_information = (
            supplier_agent_data.get(
                "missing_information",
                [],
            )
        )



        supplier_risks = supplier_agent_data.get(
            "risks",
            [],
        )



        supplier_next_actions = (
            supplier_agent_data.get(
                "next_actions",
                [],
            )
        )



        audit["supplier_agent"] = {
            "supplier_status": supplier_status,
            "risk_level": supplier_risk_level,
            "missing_information": (
                supplier_missing_information[:20]
                if isinstance(
                    supplier_missing_information,
                    list,
                )
                else []
            ),
            "risks": (
                supplier_risks[:20]
                if isinstance(
                    supplier_risks,
                    list,
                )
                else []
            ),
            "next_actions": (
                supplier_next_actions[:20]
                if isinstance(
                    supplier_next_actions,
                    list,
                )
                else []
            ),
            "evidence": supplier_agent_evidence[:20],
        }




    context["result"].audit = audit




STEPS = [
    (
        "validate_input",
        validate_input_step,
    ),
    (
        "read_documents",
        read_documents_step,
    ),
    (
        "supplier_check",
        supplier_check_step,
    ),
    (
        "documents_ai",
        documents_ai_step,
    ),
    (
        "payment_agent",
        payment_agent_step,
    ),
    (
        "find_rules",
        find_rules_step,
    ),
    (
        "calculate",
        calculate_step,
    ),
    (
        "audit",
        audit_step,
    ),
]