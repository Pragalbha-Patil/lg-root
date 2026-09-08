"""Run full JavaScript modules with DOM/Luna/filesystem mocks and real coverage."""

from pathlib import Path
import shutil
import subprocess
import unittest


class RuntimeTests(unittest.TestCase):
    def test_runtime_regressions(self):
        root = Path(__file__).resolve().parents[1]
        self.assertIsNotNone(shutil.which("node"), "Node.js is required")
        self.assertTrue((root / "node_modules/jsdom").is_dir(), "Run npm ci for host test dependencies")
        tests = sorted(str(path) for path in (root / "tests/js").glob("*.test.cjs"))
        subprocess.run(["node", "node_modules/c8/bin/c8.js", "node", "--test", "--experimental-test-isolation=none", *tests],
                       cwd=root, check=True, timeout=120)
