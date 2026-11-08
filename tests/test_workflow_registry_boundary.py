import unittest
from pathlib import Path

class WorkflowRegistryBoundaryTests(unittest.TestCase):
    def test_workflow_steps_use_unified_registry(self):
        source = Path(
            "slai/workflow/steps.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "from slai.core.capabilities import get_capabilities",
            source,
        )

        self.assertNotIn(
            "from core.agent_registry import",
            source,
        )

        self.assertNotIn(
            "from ..tools.calculator import",
            source,
        )

        self.assertNotIn(
            "from ..tools.document_reader import",
            source,
        )

        self.assertNotIn(
            "from ..tools.knowledge import",
            source,
        )

    def test_capabilities_composition_root_contains_direct_tool_imports(self):
        source = Path(
            "slai/core/capabilities/defaults.py"
        ).read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "from slai.tools.calculator import",
            source,
        )

        self.assertIn(
            "from slai.tools.document_reader import",
            source,
        )

        self.assertIn(
            "from slai.tools.knowledge import",
            source,
        )

if __name__ == "__main__":
    unittest.main()
