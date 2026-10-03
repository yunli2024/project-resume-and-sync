import importlib.util
from pathlib import Path
import unittest


class DemoTests(unittest.TestCase):
    def test_documented_demo_runs_as_a_complete_continuity_story(self):
        source = Path(__file__).resolve().parents[1] / "examples/demo.py"
        spec = importlib.util.spec_from_file_location("continuity_demo", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.run_demo()
        self.assertEqual(result["passed"], 7)


if __name__ == "__main__":
    unittest.main()
