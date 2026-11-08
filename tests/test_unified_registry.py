import unittest

from slai.core.capabilities import create_default_capabilities

class UnifiedRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = create_default_capabilities()

    def test_core_agent_is_registered(self):
        agent = self.registry.get_agent("documents_ai")

        self.assertIsNotNone(agent)
        self.assertEqual(agent.name, "documents_ai")

    def test_core_and_application_skills_are_registered(self):
        skills = {
            item["name"]
            for item in self.registry.list_skills()
        }

        self.assertIn("read_document", skills)
        self.assertIn("extract_fields", skills)
        self.assertIn("check_consistency", skills)
        self.assertIn("check_missing_documents", skills)
        self.assertIn("cost_calculator", skills)
        self.assertIn("knowledge_search", skills)
        self.assertIn("document_extract", skills)

    def test_tools_are_registered(self):
        tools = {
            item["name"]
            for item in self.registry.list_tools()
        }

        self.assertIn("calculate_full_cost", tools)
        self.assertIn("read_document", tools)
        self.assertIn("find_relevant_rules", tools)

if __name__ == "__main__":
    unittest.main()
