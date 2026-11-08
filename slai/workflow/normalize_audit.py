
import re
from copy import deepcopy

MAX_MISSING_INFORMATION = 5
MAX_RISKS = 3
MAX_RECOMMENDATIONS = 3

RISK_LEVELS = {
    "low",
    "medium",
    "high",
    "insufficient_data",
}

ALLOWED_SOURCE_VALUES = {
    "deal data",
    "uploaded document",
    "knowledge base",
    "requires verification",
}

DEFAULT_SUPPLIER_MESSAGE = {
    "chinese": (
        "请确认合同、规格、付款、运输和质量文件，"
        "并确认最终发货时间。"
    ),
    "russian_translation": (
        "Пожалуйста, подтвердите договор, спецификацию, "
        "оплату, транспортные документы и документы о качестве, "
        "а также окончательный срок отгрузки."
    ),
}

DEFAULT_LOW_RISK_SUPPLIER_MESSAGE = {
    "chinese": (
        "感谢您提供合同、发票、装箱单、付款确认和质量检验报告。"
    ),
    "russian_translation": (
        "Спасибо за предоставление договора, инвойса, упаковочного листа, "
        "подтверждения оплаты и отчёта о проверке качества."
    ),
}

def normalize_text(value):
    if not isinstance(value, str):
        return ""

    return " ".join(value.split()).strip()

def contains_cjk(value):
    if not isinstance(value, str):
        return False

    return bool(
        re.search(
            r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]",
            value,
        )
    )

def normalize_source(value):
    source = normalize_text(value)

    if not source:
        return "requires verification"

    source_lower = source.casefold()

    for allowed_source in ALLOWED_SOURCE_VALUES:
        if source_lower == allowed_source.casefold():
            return allowed_source

    rule_ids = re.findall(
        r"\b[A-Z][A-Z0-9]*(?:[-_.:][A-Z0-9]+)+\b",
        source,
        flags=re.IGNORECASE,
    )

    if rule_ids:
        return rule_ids[-1]

    if re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}",
        source,
    ):
        return source

    return "requires verification"

def normalize_risks(audit):
    if not isinstance(audit, dict):
        return audit

    risks = audit.get("risks")

    if not isinstance(risks, list):
        audit["risks"] = []
        return audit

    cleaned_risks = []

    for risk in risks:
        if not isinstance(risk, dict):
            continue

        severity = normalize_text(
            risk.get("severity", "")
        ).casefold()

        if severity not in {
            "low",
            "medium",
            "high",
        }:
            severity = ""

        cleaned_risks.append(
            {
                "title": normalize_text(
                    risk.get("title", "")
                ),
                "description": normalize_text(
                    risk.get("description", "")
                ),
                "severity": severity,
                "source": normalize_source(
                    risk.get("source", "")
                ),
            }
        )

    audit["risks"] = cleaned_risks[:MAX_RISKS]

    return audit

def normalize_missing_information(audit):
    if not isinstance(audit, dict):
        return audit

    missing_items = audit.get(
        "missing_information"
    )

    if not isinstance(missing_items, list):
        audit["missing_information"] = []
        return audit

    cleaned_items = []

    for item in missing_items:
        normalized = normalize_text(item)

        if normalized:
            cleaned_items.append(normalized)

    audit["missing_information"] = cleaned_items[
        :MAX_MISSING_INFORMATION
    ]

    return audit

def normalize_recommendations(audit):
    if not isinstance(audit, dict):
        return audit

    recommendations = audit.get(
        "recommendations"
    )

    if not isinstance(recommendations, list):
        audit["recommendations"] = []
        return audit

    cleaned_items = []

    for item in recommendations:
        normalized = normalize_text(item)

        if normalized:
            cleaned_items.append(normalized)

    audit["recommendations"] = cleaned_items[
        :MAX_RECOMMENDATIONS
    ]

    return audit

def normalize_overall_risk(audit):
    if not isinstance(audit, dict):
        return audit

    current_risk_level = audit.get(
        "risk_level",
        "insufficient_data",
    )

    if isinstance(current_risk_level, str):
        current_risk_level = (
            current_risk_level.casefold().strip()
        )
    else:
        current_risk_level = "insufficient_data"

    if current_risk_level not in RISK_LEVELS:
        current_risk_level = "insufficient_data"

    severities = set()
    risks = audit.get("risks", [])

    if isinstance(risks, list):
        for risk in risks:
            if not isinstance(risk, dict):
                continue

            severity = risk.get("severity", "")

            if isinstance(severity, str):
                severity = severity.casefold().strip()

            if severity in {
                "low",
                "medium",
                "high",
            }:
                severities.add(severity)

    if (
        current_risk_level == "high"
        or "high" in severities
    ):
        audit["risk_level"] = "high"
        return audit

    if (
        current_risk_level == "medium"
        or "medium" in severities
    ):
        audit["risk_level"] = "medium"
        return audit

    if (
        current_risk_level == "insufficient_data"
        or audit.get("missing_information")
    ):
        audit["risk_level"] = "insufficient_data"
        return audit

    audit["risk_level"] = "low"

    return audit

def is_low_risk(audit):
    if not isinstance(audit, dict):
        return False

    return audit.get("risk_level") == "low"

def normalize_supplier_message(audit):
    if not isinstance(audit, dict):
        return audit

    if is_low_risk(audit):
        audit["supplier_message"] = dict(
            DEFAULT_LOW_RISK_SUPPLIER_MESSAGE
        )
        return audit

    message = audit.get("supplier_message")

    if not isinstance(message, dict):
        audit["supplier_message"] = dict(
            DEFAULT_SUPPLIER_MESSAGE
        )
        return audit

    chinese = normalize_text(
        message.get("chinese", "")
    )

    russian_translation = normalize_text(
        message.get("russian_translation", "")
    )

    message_is_valid = (
        bool(chinese)
        and bool(russian_translation)
        and len(chinese) <= 1500
        and len(russian_translation) <= 1500
        and contains_cjk(chinese)
        and not contains_cjk(russian_translation)
    )

    if not message_is_valid:
        audit["supplier_message"] = dict(
            DEFAULT_SUPPLIER_MESSAGE
        )
        return audit

    audit["supplier_message"] = {
        "chinese": chinese,
        "russian_translation": russian_translation,
    }

    return audit

def normalize_audit(audit):
    if not isinstance(audit, dict):
        return {
            "risk_level": "insufficient_data",
            "missing_information": [],
            "risks": [],
            "recommendations": [],
            "supplier_message": dict(
                DEFAULT_SUPPLIER_MESSAGE
            ),
        }

    normalized = deepcopy(audit)

    normalize_risks(normalized)
    normalize_missing_information(normalized)
    normalize_recommendations(normalized)

    normalize_overall_risk(normalized)
    normalize_supplier_message(normalized)

    return normalized
