import unittest

from slai.core.capabilities import (
    get_capabilities,
    reset_capabilities,
)

class CapabilitiesFactoryTests(unittest.TestCase):
    def setUp(self):
        reset_capabilities()

    def tearDown(self):
        reset_capabilities()

    def test_factory_returns_unified_registry(self):
        registry = get_capabilities()

        self.assertIsNotNone(registry)
        self.assertIsNotNone(
            registry.get_agent("documents_ai")
        )

    def test_factory_reuses_registry_in_process(self):
        first = get_capabilities()
        second = get_capabilities()

        self.assertIs(first, second)

    def test_factory_registry_can_run_skill(self):
        registry = get_capabilities()

        result = registry.run_skill(
            "cost_calculator",
            {
                "deal": {
                    "quantity": 2,
                    "unit_price": 50,
                },
            },
        )

        self.assertEqual(result["skill"], "cost_calculator")
        self.assertEqual(result["result"]["total_cost"], 100.0)

if __name__ == "__main__":
    unittest.main()
