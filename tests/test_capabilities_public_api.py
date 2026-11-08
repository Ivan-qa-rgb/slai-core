import unittest

from slai.core import (
    get_capabilities,
    reset_capabilities,
)
from slai.core.capabilities import UnifiedRegistry

class CapabilitiesPublicAPITests(unittest.TestCase):
    def setUp(self):
        reset_capabilities()

    def tearDown(self):
        reset_capabilities()

    def test_capabilities_are_available_from_slai_core(self):
        registry = get_capabilities()

        self.assertIsInstance(
            registry,
            UnifiedRegistry,
        )

    def test_public_api_returns_cached_registry(self):
        first = get_capabilities()
        second = get_capabilities()

        self.assertIs(first, second)

    def test_public_api_exposes_expected_capabilities(self):
        registry = get_capabilities()

        skill_names = {
            item["name"]
            for item in registry.list_skills()
        }

        tool_names = {
            item["name"]
            for item in registry.list_tools()
        }

        self.assertIn(
            "documents_ai",
            {
                item["name"]
                for item in registry.list_agents()
            },
        )

        self.assertIn(
            "cost_calculator",
            skill_names,
        )

        self.assertIn(
            "read_document",
            tool_names,
        )

        self.assertIn(
            "find_relevant_rules",
            tool_names,
        )

        self.assertIn(
            "calculate_supply_cost",
            tool_names,
        )

if __name__ == "__main__":
    unittest.main()
