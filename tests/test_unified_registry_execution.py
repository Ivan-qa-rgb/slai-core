import unittest

from slai.core.capabilities import create_default_capabilities

class UnifiedRegistryExecutionTests(unittest.TestCase):
    def setUp(self):
        self.registry = create_default_capabilities()

        self.document = {
            "id": 1,
            "file_name": "contract.txt",
            "document_type": "contract",
            "extracted_text": (
                "Product: LED lamp A60 9W E27 3000K\n"
                "Quantity: 20\n"
                "Currency: CNY\n"
                "Total amount: 28000"
            ),
        }

    def test_read_document_runs_through_unified_registry(self):
        result = self.registry.run_skill(
            "read_document",
            {
                "document": self.document,
            },
        )

        self.assertIsInstance(result, dict)

    def test_extract_fields_runs_through_unified_registry(self):
        result = self.registry.run_skill(
            "extract_fields",
            {
                "document": self.document,
            },
        )

        self.assertIsInstance(result, dict)

    def test_consistency_checker_runs_through_unified_registry(self):
        result = self.registry.run_skill(
            "check_consistency",
            {
                "documents": [
                    self.document,
                    {
                        "id": 2,
                        "file_name": "specification.txt",
                        "document_type": "specification",
                        "extracted_text": (
                            "Product: LED lamp A60 9W E27 3000K\n"
                            "Quantity: 20\n"
                            "Currency: CNY"
                        ),
                    },
                ],
            },
        )

        self.assertIsInstance(result, list)

    def test_missing_documents_checker_runs_through_unified_registry(self):
        result = self.registry.run_skill(
            "check_missing_documents",
            {
                "documents": [],
            },
        )

        self.assertIsInstance(result, list)

if __name__ == "__main__":
    unittest.main()
