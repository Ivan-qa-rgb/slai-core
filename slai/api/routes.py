import json
import math
import base64
import io



from pypdf import PdfReader
from docx import Document as DocxDocument



from ..db import get_connection, get_documents_for_deal
from ..models import Deal
from ..workflow.engine import run_workflow




ALLOWED_DOCUMENT_TYPES = {
    "contract",
    "specification",
    "payment",
    "quality",
    "other",
}




MAX_DOCUMENT_TEXT = 2 * 1024 * 1024





_EXPORT_MARKERS = (
    "экспорт",
    "export",
    "出口",
    "清关",
    "customs clearance",
    "export clearance",
)


def _contains_export_reference(value):
    if value is None:
        return False


    normalized = " ".join(
        str(value).casefold().split()
    )


    return any(
        marker in normalized
        for marker in _EXPORT_MARKERS
    )


def _clean_supplier_message(result):
    """
    Удаляет сведения об экспортном оформлении
    из результата, предназначенного поставщику.
    """


    if not hasattr(result, "audit"):
        raise ValueError(
            "result must contain audit"
        )


    audit = result.audit


    if not isinstance(audit, dict):
        result.audit = {}
        return result


    cleaned_audit = dict(audit)


    missing_information = audit.get(
        "missing_information",
        [],
    )


    if not isinstance(missing_information, list):
        missing_information = []


    cleaned_audit["missing_information"] = [
        item
        for item in missing_information
        if not _contains_export_reference(item)
    ]


    risks = audit.get("risks", [])


    if not isinstance(risks, list):
        risks = []


    cleaned_audit["risks"] = [
        risk
        for risk in risks
        if not _contains_export_reference(
            risk.get("title", "")
            if isinstance(risk, dict)
            else risk
        )
        and not _contains_export_reference(
            risk.get("description", "")
            if isinstance(risk, dict)
            else ""
        )
    ]


    recommendations = audit.get(
        "recommendations",
        [],
    )


    if not isinstance(recommendations, list):
        recommendations = []


    cleaned_audit["recommendations"] = [
        item
        for item in recommendations
        if not _contains_export_reference(item)
    ]


    supplier_message = audit.get(
        "supplier_message",
        {},
    )


    if not isinstance(supplier_message, dict):
        supplier_message = {}


    cleaned_audit["supplier_message"] = {
        key: value
        for key, value in supplier_message.items()
        if not _contains_export_reference(value)
    }


    result.audit = cleaned_audit
    return result


def build_supplier_view(audit):
    if not isinstance(audit, dict):
        raise ValueError("audit result must be an object")




    risks = audit.get("risks", [])
    missing_information = audit.get("missing_information", [])
    recommendations = audit.get("recommendations", [])




    if not isinstance(risks, list):
        risks = []




    if not isinstance(missing_information, list):
        missing_information = []




    if not isinstance(recommendations, list):
        recommendations = []




    supplier_risks = [
        risk
        for risk in risks
        if isinstance(risk, dict)
        and "экспорт" not in str(risk.get("title", "")).lower()
        and "экспорт" not in str(risk.get("description", "")).lower()
    ]




    supplier_missing = [
        item
        for item in missing_information
        if isinstance(item, str)
        and "экспорт" not in item.lower()
    ]




    supplier_recommendations = [
        item
        for item in recommendations
        if isinstance(item, str)
        and "экспорт" not in item.lower()
    ]




    supplier_message = audit.get("supplier_message", {})




    if not isinstance(supplier_message, dict):
        supplier_message = {}




    payment_agent = audit.get("payment_agent", {})


    if not isinstance(payment_agent, dict):
        payment_agent = {}




    supplier_agent = audit.get("supplier_agent", {})


    if not isinstance(supplier_agent, dict):
        supplier_agent = {}




    return {
        "risk_level": audit.get("risk_level", "insufficient_data"),
        "missing_information": supplier_missing,
        "risks": supplier_risks,
        "recommendations": supplier_recommendations,
        "supplier_message": supplier_message,
        "payment_agent": payment_agent,
        "supplier_agent": supplier_agent,
    }


def positive_int(value, field_name):
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer")



    if result <= 0:
        raise ValueError(f"{field_name} must be positive")



    return result




def non_negative_money(value, field_name):
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a number")



    if not math.isfinite(result) or result < 0:
        raise ValueError(
            f"{field_name} must be finite and non-negative"
        )



    return result




def create_deal(data):
    deal = Deal(
        supplier_name=str(data.get("supplier_name", "")).strip(),
        product_name=str(data.get("product_name", "")).strip(),
        quantity=positive_int(data.get("quantity"), "quantity"),
        unit_price=non_negative_money(
            data.get("unit_price"),
            "unit_price",
        ),
        currency=str(data.get("currency", "CNY")).strip(),
        incoterm=str(data.get("incoterm", "")).strip(),
        payment_terms=str(data.get("payment_terms", "")).strip(),
        production_days=positive_int(
            data.get("production_days"),
            "production_days",
        ),
        status="ready",
    )



    if not deal.supplier_name:
        raise ValueError("supplier_name is required")



    if not deal.product_name:
        raise ValueError("product_name is required")



    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO deals (
                supplier_name,
                product_name,
                quantity,
                unit_price,
                currency,
                incoterm,
                payment_terms,
                production_days,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                deal.supplier_name,
                deal.product_name,
                deal.quantity,
                deal.unit_price,
                deal.currency,
                deal.incoterm,
                deal.payment_terms,
                deal.production_days,
                deal.status,
            ),
        )
        deal.id = cursor.lastrowid



    return deal




def get_deal(deal_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM deals WHERE id = ?",
            (deal_id,),
        ).fetchone()



    if not row:
        raise ValueError("deal not found")



    return Deal(
        id=row["id"],
        supplier_name=row["supplier_name"],
        product_name=row["product_name"],
        quantity=row["quantity"],
        unit_price=row["unit_price"],
        currency=row["currency"],
        incoterm=row["incoterm"],
        payment_terms=row["payment_terms"],
        production_days=row["production_days"],
        status=row["status"],
    )




def get_deal_documents(deal_id):
    deal = get_deal(int(deal_id))


    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                file_name,
                document_type,
                extracted_text
            FROM documents
            WHERE deal_id = ?
            ORDER BY id
            """,
            (deal.id,),
        ).fetchall()


    documents = []


    for number, row in enumerate(rows, start=1):
        documents.append(
            {
                "id": row["id"],
                "file_name": row["file_name"],
                "document_type": row["document_type"],
                "content_length": len(row["extracted_text"] or ""),
                "number": number,
            }
        )


    return documents




def get_audit_history(deal_id):
    deal = get_deal(int(deal_id))


    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                run_id,
                audit_json,
                is_valid
            FROM audit_results
            WHERE deal_id = ?
            ORDER BY id DESC
            """,
            (deal.id,),
        ).fetchall()


    history = []


    for row in rows:
        try:
            audit = json.loads(row["audit_json"] or "{}")
        except Exception:
            audit = {}


        history.append(
            {
                "id": row["id"],
                "run_id": row["run_id"],
                "is_valid": bool(row["is_valid"]),
                "risk_level": audit.get("risk_level", "unknown"),
                "risks": audit.get("risks", []),
                "recommendations": audit.get("recommendations", []),
                "missing_information": audit.get(
                    "missing_information",
                    [],
                ),
            }
        )


    return history




def run_deal_audit(deal_id, documents=None, thread_id=None):
    deal = get_deal(int(deal_id))



    if documents is None:
        documents = get_documents_for_deal(deal.id)



    result = run_workflow(deal, documents, thread_id=thread_id)



    if result.status != "completed":
        return {
            "status": result.status,
            "deal_id": result.deal_id,
            "thread_id": result.thread_id,
            "missing_fields": result.missing_fields,
            "errors": result.errors,
        }



    result = _clean_supplier_message(result)


    response = build_supplier_view(result.audit)
    response["calculation"] = result.calculation
    response["status"] = "completed"
    response["deal_id"] = result.deal_id
    response["thread_id"] = result.thread_id



    return response




def run_audit_from_payload(data):
    deal_id = data.get("deal_id")
    thread_id = data.get("thread_id")



    if not deal_id:
        raise ValueError("deal_id is required for audit")



    return run_deal_audit(
        int(deal_id),
        thread_id=thread_id,
    )




def save_document(deal_id, data):
    deal = get_deal(int(deal_id))



    file_name = data.get("file_name")
    document_type = data.get("document_type", "")
    extracted_text = data.get("extracted_text", "")
    pdf_base64 = data.get("pdf_base64", "")
    docx_base64 = data.get("docx_base64", "")



    if pdf_base64 and docx_base64:
        raise ValueError(
            "send either pdf_base64 or docx_base64, not both"
        )



    if pdf_base64:
        try:
            pdf_bytes = base64.b64decode(pdf_base64, validate=True)
        except Exception:
            raise ValueError("invalid PDF file")



        if not pdf_bytes.startswith(b"%PDF"):
            raise ValueError("invalid PDF file")



        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            pages = []



            for page in reader.pages:
                page_text = page.extract_text() or ""
                pages.append(page_text)



            extracted_text = "\n\n".join(pages).strip()
        except Exception:
            raise ValueError("could not extract text from PDF")



        if not extracted_text:
            raise ValueError(
                "PDF does not contain extractable text. "
                "Scanned PDF requires OCR."
            )



    if docx_base64:
        try:
            docx_bytes = base64.b64decode(docx_base64, validate=True)
        except Exception:
            raise ValueError("invalid DOCX file")



        try:
            docx_document = DocxDocument(io.BytesIO(docx_bytes))
            paragraphs = []



            for paragraph in docx_document.paragraphs:
                if paragraph.text.strip():
                    paragraphs.append(paragraph.text)



            for table in docx_document.tables:
                for row in table.rows:
                    row_text = " | ".join(
                        cell.text.strip()
                        for cell in row.cells
                    )



                    if row_text.strip(" |"):
                        paragraphs.append(row_text)



            extracted_text = "\n".join(paragraphs).strip()
        except Exception:
            raise ValueError("could not extract text from DOCX")



        if not extracted_text:
            raise ValueError("DOCX does not contain extractable text")



    if not isinstance(file_name, str) or not file_name.strip():
        raise ValueError("file_name is required")



    file_name = file_name.strip()



    if len(file_name) > 255:
        raise ValueError("file_name is too long")



    if "\x00" in file_name or "\n" in file_name or "\r" in file_name:
        raise ValueError("file_name contains invalid characters")



    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise ValueError("unsupported document type")



    if not isinstance(extracted_text, str):
        raise ValueError("extracted_text must be a string")



    if len(extracted_text.encode("utf-8")) > MAX_DOCUMENT_TEXT:
        raise ValueError("document is too large")



    with get_connection() as conn:
        duplicate = conn.execute(
            """
            SELECT id
            FROM documents
            WHERE deal_id = ?
              AND file_name = ?
              AND document_type = ?
              AND extracted_text = ?
            LIMIT 1
            """,
            (
                deal.id,
                file_name,
                document_type,
                extracted_text,
            ),
        ).fetchone()

    if duplicate:
        raise ValueError("duplicate document already uploaded")

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (
                deal_id,
                file_name,
                file_path,
                document_type,
                extracted_text
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                deal.id,
                file_name,
                "",
                document_type,
                extracted_text,
            ),
        )
        document_id = cursor.lastrowid

    return {
        "status": "uploaded",
        "id": document_id,
        "deal_id": deal.id,
        "file_name": file_name,
        "document_type": document_type,
        "content_length": len(extracted_text),
    }