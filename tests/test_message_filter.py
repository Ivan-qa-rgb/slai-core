import unittest

from slai.api.routes import _clean_supplier_message

class FakeResult:
    def __init__(self, audit):
        self.audit = audit

class SupplierMessageFilterTests(unittest.TestCase):
    def test_export_information_is_removed(self):
        audit = {
            "risk_level": "insufficient_data",
            "missing_information": [
                "документы, подтверждающие экспортное оформление",
                "документы о качестве",
                "подтверждение готовности товара к отгрузке",
            ],
            "risks": [
                {
                    "title": "тсутствие экспортного оформления",
                    "description": (
                        "ет документов для экспортного оформления."
                    ),
                    "severity": "high",
                },
                {
                    "title": "ет документа о качестве",
                    "description": "ачество не подтверждено.",
                    "severity": "medium",
                },
            ],
            "recommendations": [
                (
                    "обавьте документ, подтверждающий "
                    "экспортное оформление."
                ),
                "обавьте документ о качестве.",
            ],
            "supplier_message": {
                "chinese": "请提供出口清关文件。",
                "russian_translation": (
                    "ожалуйста, предоставьте документы "
                    "для экспортного оформления."
                ),
            },
        }

        result = _clean_supplier_message(
            FakeResult(audit)
        )

        self.assertEqual(
            result.audit["missing_information"],
            [
                "документы о качестве",
                "подтверждение готовности товара к отгрузке",
            ],
        )

        self.assertEqual(
            result.audit["risks"],
            [
                {
                    "title": "ет документа о качестве",
                    "description": "ачество не подтверждено.",
                    "severity": "medium",
                }
            ],
        )

        self.assertEqual(
            result.audit["recommendations"],
            [
                "обавьте документ о качестве.",
            ],
        )

        self.assertEqual(
            result.audit["supplier_message"],
            {},
        )

    def test_non_export_information_is_preserved(self):
        audit = {
            "missing_information": [
                "документы о качестве",
            ],
            "risks": [
                {
                    "title": "Проблема с качеством",
                    "description": "Качество не подтверждено.",
                    "severity": "medium",
                }
            ],
            "recommendations": [
                "Добавьте документ о качестве.",
            ],
            "supplier_message": {
                "russian_translation": (
                    "Пожалуйста, предоставьте документ о качестве."
                ),
            },
        }

        result = _clean_supplier_message(
            FakeResult(audit)
        )

        self.assertEqual(
            result.audit["missing_information"],
            audit["missing_information"],
        )

        self.assertEqual(
            result.audit["risks"],
            audit["risks"],
        )

        self.assertEqual(
            result.audit["recommendations"],
            audit["recommendations"],
        )

        self.assertEqual(
            result.audit["supplier_message"],
            audit["supplier_message"],
        )

if __name__ == "__main__":
    unittest.main()
