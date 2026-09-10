"""Execute the shipped release-archive recipe using only synthetic host command stubs."""

import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

from tools.check import find_shell

ROOT = Path(__file__).resolve().parents[1]
SHELL = find_shell()


@unittest.skipUnless(SHELL, "POSIX sh is required for documentation recipe tests")
class ReleaseRecipeTest(unittest.TestCase):
    def run_recipe(self, **overrides):
        guide = (ROOT / "docs/INSTALL.md").read_text(encoding="utf-8")
        blocks = re.findall(r"```sh\n(.*?)```", guide, flags=re.S)
        recipe = next(block for block in blocks if "sha256sum -c" in block)
        # Functions intercept these names so no checksum, extraction, or
        # network access runs in these tests.
        stubs = (
            "sha256sum() { printf 'checksum\\n' >&2; return \"$CHECK_EXIT\"; }\n"
            "tar() { printf 'extract\\n' >&2; return \"$TAR_EXIT\"; }\n"
        )
        env = dict(os.environ, CHECK_EXIT="0", TAR_EXIT="0")
        env.update(overrides)
        return subprocess.run([SHELL], input=stubs + recipe, cwd=ROOT,
                              env=env, capture_output=True, text=True,
                              encoding="utf-8", timeout=10)

    def test_checksum_failure_prevents_extraction(self):
        result = self.run_recipe(CHECK_EXIT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("extract", result.stderr)

    def test_extraction_failure_is_not_success(self):
        result = self.run_recipe(TAR_EXIT="1")
        self.assertNotEqual(result.returncode, 0)

    def test_successful_recipe_verifies_then_extracts(self):
        result = self.run_recipe()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr.splitlines(), ["checksum", "extract"])


if __name__ == "__main__":
    unittest.main()
