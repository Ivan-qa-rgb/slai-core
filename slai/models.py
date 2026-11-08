from __future__ import annotations

from dataclasses import asdict, dataclass, field
from numbers import Real
from typing import Any

PERSISTED_DEAL_FIELDS = (
    "supplier_name",
    "product_name",
    "quantity",
    "unit_price",
    "currency",
    "incoterm",
    "payment_terms",
    "production_days",
    "status",
)

CALCULATION_FIELDS = (
    "hs_code",
    "duty_rate",
    "vat_rate",
    "customs_fee",
    "logistics_cost",
    "brokerage_fee",
    "certification_cost",
    "other_costs",
)

def _validate_text(
    field_name: str,
    value: Any,
    *,
    required: bool = False,
) -> str:
    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} должен быть строкой"
        )

    value = value.strip()

    if required and not value:
        raise ValueError(
            f"{field_name} обязателен"
        )

    return value

def _validate_non_negative_number(
    field_name: str,
    value: Any,
) -> int | float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(
            f"{field_name} должен быть числом"
        )

    if value < 0:
        raise ValueError(
            f"{field_name} не может быть отрицательным"
        )

    return value

def _validate_rate(
    field_name: str,
    value: Any,
) -> float:
    value = _validate_non_negative_number(
        field_name,
        value,
    )

    if value > 100:
        raise ValueError(
            f"{field_name} должен быть в диапазоне от 0 до 100"
        )

    return float(value)

@dataclass
class Deal:
    """Модель сделки и её расчётных параметров."""

    id: int | None = None

    supplier_name: str = ""
    product_name: str = ""
    quantity: int = 0
    unit_price: float = 0.0
    currency: str = "CNY"
    incoterm: str = ""
    payment_terms: str = ""
    production_days: int = 0
    status: str = "draft"

    hs_code: str = ""
    duty_rate: float = 0.0
    vat_rate: float = 0.0
    customs_fee: float = 0.0
    logistics_cost: float = 0.0
    brokerage_fee: float = 0.0
    certification_cost: float = 0.0
    other_costs: float = 0.0

    def __post_init__(self) -> None:
        if self.id is not None:
            if isinstance(self.id, bool) or not isinstance(
                self.id,
                int,
            ):
                raise ValueError(
                    "id должен быть целым числом"
                )

            if self.id <= 0:
                raise ValueError(
                    "id должен быть больше нуля"
                )

        self.supplier_name = _validate_text(
            "supplier_name",
            self.supplier_name,
        )

        self.product_name = _validate_text(
            "product_name",
            self.product_name,
        )

        self.currency = _validate_text(
            "currency",
            self.currency,
        ).upper()

        self.incoterm = _validate_text(
            "incoterm",
            self.incoterm,
        )

        self.payment_terms = _validate_text(
            "payment_terms",
            self.payment_terms,
        )

        self.status = _validate_text(
            "status",
            self.status,
            required=True,
        )

        self.hs_code = _validate_text(
            "hs_code",
            self.hs_code,
        )

        if isinstance(self.quantity, bool) or not isinstance(
            self.quantity,
            int,
        ):
            raise ValueError(
                "quantity должен быть целым числом"
            )

        if self.quantity < 0:
            raise ValueError(
                "quantity не может быть отрицательным"
            )

        if isinstance(self.production_days, bool):
            raise ValueError(
                "production_days должен быть целым числом"
            )

        if not isinstance(self.production_days, int):
            raise ValueError(
                "production_days должен быть целым числом"
            )

        if self.production_days < 0:
            raise ValueError(
                "production_days не может быть отрицательным"
            )

        self.unit_price = float(
            _validate_non_negative_number(
                "unit_price",
                self.unit_price,
            )
        )

        self.duty_rate = _validate_rate(
            "duty_rate",
            self.duty_rate,
        )

        self.vat_rate = _validate_rate(
            "vat_rate",
            self.vat_rate,
        )

        self.customs_fee = float(
            _validate_non_negative_number(
                "customs_fee",
                self.customs_fee,
            )
        )

        self.logistics_cost = float(
            _validate_non_negative_number(
                "logistics_cost",
                self.logistics_cost,
            )
        )

        self.brokerage_fee = float(
            _validate_non_negative_number(
                "brokerage_fee",
                self.brokerage_fee,
            )
        )

        self.certification_cost = float(
            _validate_non_negative_number(
                "certification_cost",
                self.certification_cost,
            )
        )

        self.other_costs = float(
            _validate_non_negative_number(
                "other_costs",
                self.other_costs,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        """Возвращает полное представление сделки."""
        return asdict(self)

    def to_storage_dict(
        self,
        *,
        include_id: bool = False,
    ) -> dict[str, Any]:
        """
        Возвращает только поля, поддерживаемые текущей БД.

        Расчётные поля не включаются.
        """
        result = {
            field_name: getattr(self, field_name)
            for field_name in PERSISTED_DEAL_FIELDS
        }

        if include_id and self.id is not None:
            result["id"] = self.id

        return result

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "Deal":
        """Создаёт Deal из словаря."""
        if not isinstance(data, dict):
            raise TypeError(
                "Данные сделки должны быть объектом"
            )

        allowed_fields = {
            field_name
            for field_name in (
                PERSISTED_DEAL_FIELDS
                + CALCULATION_FIELDS
                + ("id",)
            )
        }

        filtered_data = {
            key: value
            for key, value in data.items()
            if key in allowed_fields
        }

        return cls(**filtered_data)

@dataclass
class WorkflowResult:
    """Результат выполнения workflow сделки."""

    status: str
    deal_id: int | None = None
    thread_id: str | None = None
    missing_fields: list[dict[str, Any]] = field(
        default_factory=list
    )
    documents: list[dict[str, Any]] = field(
        default_factory=list
    )
    calculation: dict[str, Any] = field(
        default_factory=dict
    )
    audit: dict[str, Any] = field(
        default_factory=dict
    )
    errors: list[dict[str, Any]] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        self.status = _validate_text(
            "status",
            self.status,
            required=True,
        )

        if self.deal_id is not None:
            if isinstance(self.deal_id, bool) or not isinstance(
                self.deal_id,
                int,
            ):
                raise ValueError(
                    "deal_id должен быть целым числом"
                )

            if self.deal_id <= 0:
                raise ValueError(
                    "deal_id должен быть больше нуля"
                )

        if not isinstance(self.missing_fields, list):
            raise TypeError(
                "missing_fields должен быть списком"
            )

        if not isinstance(self.documents, list):
            raise TypeError(
                "documents должен быть списком"
            )

        if not isinstance(self.calculation, dict):
            raise TypeError(
                "calculation должен быть объектом"
            )

        if not isinstance(self.audit, dict):
            raise TypeError(
                "audit должен быть объектом"
            )

        if not isinstance(self.errors, list):
            raise TypeError(
                "errors должен быть списком"
            )

    def to_dict(self) -> dict[str, Any]:
        """Преобразует результат workflow в словарь."""
        return asdict(self)

