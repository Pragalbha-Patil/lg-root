"""Execute the shipped upload recipe using only synthetic host command stubs."""

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
        self.assertIn("scp -r launcher-app/.", recipe)
        # Functions always intercept these names, even when sh changes PATH on
        # startup. No checksum, extraction, copy, or real SSH runs in these tests.
        stubs = r'''
copies=0
sha256sum() { printf 'checksum\n' >&2; return "$CHECK_EXIT"; }
tar() { printf 'extract\n' >&2; return "$TAR_EXIT"; }
ssh() {
    case "$*" in
        *luna-send*) printf 'launch\n' >&2; printf '%s\n' "$MH_RESPONSE"; return "$LAUNCH_EXIT" ;;
        *) printf 'mkdir\n' >&2; return "$MKDIR_EXIT" ;;
    esac
}
scp() {
    copies=$((copies + 1))
    printf 'copy%s\n' "$copies" >&2
    if [ "$copies" = "$FAIL_COPY" ]; then return 1; fi
    return 0
}
'''
        env = dict(os.environ, PYTHON=Path(sys.executable).as_posix(),
                   CHECK_EXIT="0", TAR_EXIT="0", MKDIR_EXIT="0", FAIL_COPY="0",
                   LAUNCH_EXIT="0", MH_RESPONSE='{"returnValue":true}')
        env.update(overrides)
        return subprocess.run([SHELL], input=stubs + recipe, cwd=ROOT,
                              env=env, capture_output=True, text=True,
                              encoding="utf-8", timeout=10)

    def test_prerequisite_failures_prevent_later_steps(self):
        cases = (("CHECK_EXIT", "1", "extract"), ("TAR_EXIT", "1", "mkdir"),
                 ("MKDIR_EXIT", "255", "copy1"), ("FAIL_COPY", "1", "copy2"),
                 ("FAIL_COPY", "2", "launch"))
        for key, value, forbidden in cases:
            with self.subTest(key=key, value=value):
                result = self.run_recipe(**{key: value})
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(forbidden, result.stderr)

    def test_transport_and_luna_failure_are_not_success(self):
        for override in ({"LAUNCH_EXIT": "255"}, {"MH_RESPONSE": '{"returnValue":false}'},
                         {"MH_RESPONSE": "not JSON"}, {"MH_RESPONSE": '{"returnValue":1}'}):
            with self.subTest(override=override):
                result = self.run_recipe(**override)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("launch", result.stderr)

    def test_successful_recipe_runs_all_steps(self):
        result = self.run_recipe()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr.splitlines(), ["checksum", "extract", "mkdir", "copy1", "copy2", "launch"])


if __name__ == "__main__":
    unittest.main()
