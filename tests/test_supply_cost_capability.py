import unittest

from slai.core.capabilities import (
    get_capabilities,
    reset_capabilities,
)

class SupplyCostCapabilityTests(unittest.TestCase):
    def setUp(self):
        reset_capabilities()

    def tearDown(self):
        reset_capabilities()

    def test_supply_cost_tool_is_registered(self):
        registry = get_capabilities()

        tool_names = {
            item["name"]
            for item in registry.list_tools()
        }

        self.assertIn(
            "calculate_supply_cost",
            tool_names,
        )

if __name__ == "__main__":
    unittest.main()
