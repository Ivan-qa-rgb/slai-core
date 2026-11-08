import unittest
from unittest.mock import patch
from uuid import uuid4

from slai.core import reset_capabilities
from slai.db import get_connection
from slai.models import Deal
from slai.workflow.engine import run_workflow

def fake_request_audit(
    *,
    deal,
    documents,
    calculation,
    rules,
    response_schema,
    documents_ai,
):
    return {
        "risk_level": "low",
        "missing_information": [],
        "risks": [],
        "recommendations": [],
        "supplier_message": {
            "chinese": (
                "\u8bf7\u786e\u8ba4\u5408\u540c\u548c\u6700\u7ec8\u53d1\u8d27\u65f6\u95f4\u3002"
            ),
            "russian_translation": (
                "Пожалуйста, подтвердите договор "
                "и окончательную дату отгрузки."
            ),
        },
    }

class WorkflowIntegrationTests(unittest.TestCase):
    def setUp(self):
        reset_capabilities()

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
                    "Test Supplier",
                    "Test Product",
                    2,
                    50.0,
                    "CNY",
                    "FOB",
                    "30% deposit, 70% before shipment",
                    20,
                    "ready",
                ),
            )

            self.deal_id = cursor.lastrowid

        self.deal = Deal(
            id=self.deal_id,
            supplier_name="Test Supplier",
            product_name="Test Product",
            quantity=2,
            unit_price=50.0,
            currency="CNY",
            incoterm="FOB",
            payment_terms="30% deposit, 70% before shipment",
            production_days=20,
            status="ready",
        )

    def tearDown(self):
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM documents WHERE deal_id = ?",
                (self.deal_id,),
            )

            conn.execute(
                "DELETE FROM audit_results WHERE deal_id = ?",
                (self.deal_id,),
            )

            conn.execute(
                "DELETE FROM workflow_runs WHERE deal_id = ?",
                (self.deal_id,),
            )

            conn.execute(
                "DELETE FROM deals WHERE id = ?",
                (self.deal_id,),
            )

        reset_capabilities()

    def test_full_workflow_runs_without_real_llm(self):
        documents = [
            {
                "file_name": "test_contract.txt",
                "document_type": "contract",
                "extracted_text": (
                    "Contract TEST-001. "
                    "Payment: 30% deposit, "
                    "70% before shipment. "
                    "Incoterm: FOB."
                ),
            },
            {
                "file_name": "test_specification.txt",
                "document_type": "specification",
                "extracted_text": (
                    "Product: Test Product. "
                    "Quantity: 2. "
                    "Unit price: 50 CNY."
                ),
            },
        ]

        thread_id = "integration-" + uuid4().hex

        with patch(
            "slai.workflow.steps.request_audit",
            side_effect=fake_request_audit,
        ) as mocked_request_audit:
            result = run_workflow(
                self.deal,
                documents,
                thread_id=thread_id,
            )

        self.assertEqual(
            result.status,
            "completed",
        )

        self.assertEqual(
            result.thread_id,
            thread_id,
        )

        self.assertTrue(
            result.documents
        )

        self.assertIsInstance(
            result.calculation,
            dict,
        )

        self.assertEqual(
            result.audit["risk_level"],
            "low",
        )

        self.assertEqual(
            result.audit["missing_information"],
            [],
        )

        self.assertEqual(
            mocked_request_audit.call_count,
            1,
        )

    def test_workflow_fails_for_invalid_document(self):
        documents = [
            {
                "file_name": "broken_document.txt",
                "document_type": "contract",
            },
        ]

        thread_id = "integration-invalid-" + uuid4().hex

        with patch(
            "slai.workflow.steps.request_audit",
            side_effect=fake_request_audit,
        ) as mocked_request_audit:
            result = run_workflow(
                self.deal,
                documents,
                thread_id=thread_id,
            )

        self.assertEqual(
            result.status,
            "failed",
        )


        self.assertEqual(
            mocked_request_audit.call_count,
            0,
        )

    def test_workflow_uses_cached_capabilities_registry(self):
        from slai.core import get_capabilities

        first = get_capabilities()
        second = get_capabilities()

        self.assertIs(
            first,
            second,
        )

if __name__ == "__main__":
    unittest.main()
