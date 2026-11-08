import unittest

from slai.core import (
    get_capabilities,
    reset_capabilities,
)

class CapabilitiesResetTests(unittest.TestCase):
    def setUp(self):
        reset_capabilities()

    def tearDown(self):
        reset_capabilities()

    def test_registry_is_cached_until_reset(self):
        first = get_capabilities()
        second = get_capabilities()

        self.assertIs(
            first,
            second,
        )

    def test_reset_creates_new_registry(self):
        first = get_capabilities()

        reset_capabilities()

        second = get_capabilities()

        self.assertIsNot(
            first,
            second,
        )

    def test_reset_restores_default_capabilities(self):
        first = get_capabilities()

        expected_tools = {
            item["name"]
            for item in first.list_tools()
        }

        expected_agents = {
            item["name"]
            for item in first.list_agents()
        }

        reset_capabilities()

        second = get_capabilities()

        actual_tools = {
            item["name"]
            for item in second.list_tools()
        }

        actual_agents = {
            item["name"]
            for item in second.list_agents()
        }

        self.assertEqual(
            actual_tools,
            expected_tools,
        )

        self.assertEqual(
            actual_agents,
            expected_agents,
        )

        self.assertIn(
            "documents_ai",
            actual_agents,
        )

        self.assertIn(
            "read_document",
            actual_tools,
        )

        self.assertIn(
            "find_relevant_rules",
            actual_tools,
        )

        self.assertIn(
            "calculate_supply_cost",
            actual_tools,
        )

if __name__ == "__main__":
    unittest.main()
