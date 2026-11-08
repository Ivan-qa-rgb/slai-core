import unittest

from slai.core import (
    get_capabilities,
    reset_capabilities,
)

class RegistryErrorTests(unittest.TestCase):
    def setUp(self):
        reset_capabilities()
        self.registry = get_capabilities()

    def tearDown(self):
        reset_capabilities()

    def test_unknown_tool_is_rejected(self):
        with self.assertRaises(Exception):
            self.registry.get_tool(
                "tool_that_does_not_exist"
            )

    def test_unknown_agent_is_rejected(self):
        with self.assertRaises(Exception):
            self.registry.get_agent(
                "agent_that_does_not_exist"
            )

    def test_unknown_tool_cannot_be_executed(self):
        with self.assertRaises(Exception):
            self.registry.run_tool(
                "tool_that_does_not_exist",
                {},
            )

    def test_registered_tool_can_be_executed(self):
        result = self.registry.run_tool(
            "calculate_supply_cost",
            {
                "deal": {
                    "quantity": 2,
                    "unit_price": 50.0,
                },
            },
        )

        self.assertIsInstance(
            result,
            dict,
        )

if __name__ == "__main__":
    unittest.main()
