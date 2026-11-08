import re

PRIORITY_KEYWORDS = [
    "оплата",
    "депозит",
    "качество",
    "сертификат",
    "отгрузка",
    "готовность к отгрузке",
]

RISK_LEVELS = {
    "low",
    "medium",
    "high",
    "insufficient_data",
}

SEVERITIES = {
    "low",
    "medium",
    "high",
}

ALLOWED_RISK_TITLES = {
    "Корректный базис поставки",
    "Некорректный или отсутствующий базис поставки",
    "Понятные условия оплаты",
    "Неясные или отсутствующие условия оплаты",
    "Полный комплект документов",
    "Неполный комплект документов",
    "Готовность к отгрузке",
    "Риск срыва сроков отгрузки",
    "Риск качества товара",
    "Риск логистики",
    "Риск таможенного оформления",
    "Риск предоплаты",
}

ALLOWED_SOURCE_VALUES = {
    "deal data",
    "uploaded document",
    "knowledge base",
    "requires verification",
}

TOP_LEVEL_FIELDS = {
    "risk_level",
    "missing_information",
    "risks",
    "recommendations",
    "supplier_message",
    "documents_ai",
}

RISK_FIELDS = {
    "title",
    "description",
    "severity",
    "source",
}

SUPPLIER_MESSAGE_FIELDS = {
    "chinese",
    "russian_translation",
}

MAX_MISSING_INFORMATION = 5
MAX_RISKS = 3
MAX_RECOMMENDATIONS = 3

def contains_cjk(text):
    if not isinstance(text, str):
        return False

    return any(
        "\u4e00" <= character <= "\u9fff"
        for character in text
    )

def normalize_text(value):
    if not isinstance(value, str):
        return ""

    return " ".join(value.split()).strip()

def is_valid_source(value):
    if not isinstance(value, str):
        return False

    source = normalize_text(value)

    if not source or len(source) > 100:
        return False

    if source in ALLOWED_SOURCE_VALUES:
        return True

    # Разрешаем ID правила, например:
    # PAY-001, LOG-001, DOC_001, RULE.12
    return re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}",
        source,
    ) is not None

def validate_string_list(
    value,
    field_name,
    max_items,
    max_length,
):
    errors = []

    if not isinstance(value, list):
        return [
            f"{field_name} must be a list"
        ]

    if len(value) > max_items:
        errors.append(
            f"{field_name} must contain "
            f"no more than {max_items} items"
        )

    for index, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(
                f"{field_name}[{index}] must be a string"
            )
            continue

        normalized = normalize_text(item)

        if not normalized:
            errors.append(
                f"{field_name}[{index}] "
                "must be a non-empty string"
            )

        if len(normalized) > max_length:
            errors.append(
                f"{field_name}[{index}] is too long"
            )

    return errors

def validate_audit(audit):
    errors = []

    if not isinstance(audit, dict):
        return ["audit must be an object"]

    extra_fields = set(audit) - TOP_LEVEL_FIELDS

    if extra_fields:
        errors.append(
            "audit contains unsupported fields: "
            + ", ".join(sorted(extra_fields))
        )

    risk_level = audit.get("risk_level")

    if risk_level not in RISK_LEVELS:
        errors.append("invalid risk_level")

    missing_information = audit.get(
        "missing_information"
    )

    errors.extend(
        validate_string_list(
            value=missing_information,
            field_name="missing_information",
            max_items=MAX_MISSING_INFORMATION,
            max_length=500,
        )
    )

    recommendations = audit.get(
        "recommendations"
    )

    errors.extend(
        validate_string_list(
            value=recommendations,
            field_name="recommendations",
            max_items=MAX_RECOMMENDATIONS,
            max_length=500,
        )
    )

    risks = audit.get("risks")

    if not isinstance(risks, list):
        errors.append("risks must be a list")
    else:
        if len(risks) > MAX_RISKS:
            errors.append(
                f"risks must contain no more than "
                f"{MAX_RISKS} items"
            )

        for index, risk in enumerate(risks):
            if not isinstance(risk, dict):
                errors.append(
                    f"risks[{index}] must be an object"
                )
                continue

            extra_risk_fields = (
                set(risk) - RISK_FIELDS
            )

            if extra_risk_fields:
                errors.append(
                    f"risks[{index}] contains "
                    "unsupported fields: "
                    + ", ".join(
                        sorted(extra_risk_fields)
                    )
                )

            title = risk.get("title")
            description = risk.get("description")
            severity = risk.get("severity")
            source = risk.get("source")

            if not isinstance(title, str) or not title.strip():
                errors.append(
                    f"risks[{index}].title "
                    "is required"
                )
            elif title not in ALLOWED_RISK_TITLES:
                errors.append(
                    f"risks[{index}].title "
                    "is not allowed"
                )

            if (
                not isinstance(description, str)
                or not description.strip()
            ):
                errors.append(
                    f"risks[{index}].description "
                    "is required"
                )
            elif len(description.strip()) > 1000:
                errors.append(
                    f"risks[{index}].description "
                    "is too long"
                )

            if severity not in SEVERITIES:
                errors.append(
                    f"risks[{index}].severity "
                    "is invalid"
                )

            if not is_valid_source(source):
                errors.append(
                    f"risks[{index}].source "
                    "is invalid"
                )

    message = audit.get("supplier_message")

    if not isinstance(message, dict):
        errors.append(
            "supplier_message must be an object"
        )
        return errors

    extra_message_fields = (
        set(message) - SUPPLIER_MESSAGE_FIELDS
    )

    if extra_message_fields:
        errors.append(
            "supplier_message contains "
            "unsupported fields: "
            + ", ".join(
                sorted(extra_message_fields)
            )
        )

    chinese = message.get("chinese")
    russian = message.get(
        "russian_translation"
    )

    if not isinstance(chinese, str) or not chinese.strip():
        errors.append(
            "supplier_message.chinese "
            "is required"
        )
    elif len(chinese.strip()) > 1500:
        errors.append(
            "supplier_message.chinese "
            "is too long"
        )
    elif not contains_cjk(chinese):
        errors.append(
            "supplier_message.chinese "
            "must contain Chinese characters"
        )

    if not isinstance(russian, str) or not russian.strip():
        errors.append(
            "supplier_message.russian_translation "
            "is required"
        )
    elif len(russian.strip()) > 1500:
        errors.append(
            "supplier_message.russian_translation "
            "is too long"
        )
    elif contains_cjk(russian):
        errors.append(
            "supplier_message.russian_translation "
            "must not contain Chinese characters"
        )

    return errors

def prioritize_missing_items(audit):
    if not isinstance(audit, dict):
        return audit

    missing_items = audit.get(
        "missing_information"
    )

    if not isinstance(missing_items, list):
        audit["missing_information"] = []
        return audit

    def priority(item):
        text = normalize_text(item).casefold()

        for keyword in PRIORITY_KEYWORDS:
            if keyword in text:
                return 0

        return 1

    audit["missing_information"] = sorted(
        missing_items,
        key=priority,
    )[:MAX_MISSING_INFORMATION]

    return audit
