import unittest
from core.agent_registry import create_default_registry

class DocumentsAIAgentTests(unittest.TestCase):
    def test_documents_ai_detects_product_mismatch_and_missing_readiness_doc(self):
        documents = [
            {
                "id": 1,
                "file_name": "contract.txt",
                "document_type": "contract",
                "extracted_text": (
                    "Product: LED lamp A60 9W E27 3000K\n"
                    "Quantity: 20\n"
                    "Currency: CNY\n"
                    "Total amount: 28000\n"
                    "Payment terms: 40% deposit, 60% before shipment\n"
                    "Incoterm: EXW Shenzhen"
                ),
            },
            {
                "id": 2,
                "file_name": "test_specification.txt",
                "document_type": "specification",
                "extracted_text": (
                    "Товар: светодиодные лампы LED A60 9W E27, 3000K.\n"
                    "Количество: 20\n"
                    "Валюта: CNY"
                ),
            },
            {
                "id": 3,
                "file_name": "invoice.txt",
                "document_type": "invoice",
                "extracted_text": (
                    "Product: LED lamp A60 9W E27 3000K\n"
                    "Quantity: 20\n"
                    "Unit price: 1400\n"
                    "Total amount: 28000\n"
                    "Currency: CNY\n"
                    "Payment terms: 40% deposit, 60% before shipment\n"
                    "Incoterm: EXW Shenzhen"
                ),
            },
            {
                "id": 4,
                "file_name": "packing_list.txt",
                "document_type": "packing_list",
                "extracted_text": (
                    "Product: LED lamp A60 9W E27 3000K\n"
                    "Quantity: 20"
                ),
            },
            {
                "id": 5,
                "file_name": "deposit_confirmation.txt",
                "document_type": "payment_confirmation",
                "extracted_text": (
                    "Currency: CNY\n"
                    "Total amount: 28000\n"
                    "Payment terms: 40% deposit, 60% before shipment\n"
                    "Deposit payment date: 2026-10-28"
                ),
            },
            {
                "id": 6,
                "file_name": "quality_report.txt",
                "document_type": "quality_report",
                "extracted_text": (
                    "Product: LED lamp A60 9W E27 3000K\n"
                    "Quantity: 20"
                ),
            },
        ]

        registry = create_default_registry()
        agent = registry.get("documents_ai")
        self.assertIsNotNone(agent)

        result = agent.run({
            "deal_id": 40,
            "documents": documents,
        })

        self.assertEqual(result.agent, "documents_ai")
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.data["documents"]), 6)

        missing_codes = [item["code"] for item in result.data["missing_documents"]]
        self.assertIn("DOC-READINESS", missing_codes)

if __name__ == "__main__":
    unittest.main()
