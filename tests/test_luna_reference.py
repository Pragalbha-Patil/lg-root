"""Verify docs/LUNA.md tables against the shared model and service source."""

import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node") or "node"
DUMP = (
    "const M = require('./launcher-service/model.js');"
    "console.log(JSON.stringify({defaults: M.preferences({}), choices: M.choices}));"
)


def section_lines(body, heading):
    lines = []
    active = False
    for line in body.splitlines():
        if line.startswith("## "):
            active = line == "## " + heading
        elif active:
            lines.append(line)
    return lines


def table_rows(lines):
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0].startswith("`") and cells[0].endswith("`"):
            rows.append([cell.strip("`") for cell in cells])
    return rows


def documented_contract():
    body = (ROOT / "docs/LUNA.md").read_text(encoding="utf-8")
    methods = [row[0] for row in table_rows(section_lines(body, "Methods"))]
    prefs = {}
    for row in table_rows(section_lines(body, "Preferences")):
        default = json.loads(row[1])
        try:
            allowed = json.loads(row[2])
        except ValueError:
            allowed = None
        prefs[row[0]] = (default, allowed)
    return methods, prefs


def live_contract():
    result = subprocess.run([NODE, "-e", DUMP], cwd=ROOT, capture_output=True,
                            text=True, timeout=60, check=True)
    contract = json.loads(result.stdout)
    return contract["defaults"], contract["choices"]


class LunaReferenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.methods, cls.prefs = documented_contract()
        cls.defaults, cls.choices = live_contract()

    def test_methods_match_service(self):
        registered = re.findall(r"register\('(\w+)'",
                                (ROOT / "launcher-service/service.js").read_text(encoding="utf-8"))
        self.assertEqual(sorted(self.methods), sorted(registered))

    def test_preference_keys_match_model(self):
        self.assertEqual(sorted(self.prefs), sorted(self.defaults))

    def test_preference_defaults_match_model(self):
        for key, (default, _allowed) in self.prefs.items():
            with self.subTest(key=key):
                self.assertEqual(default, self.defaults[key])

    def test_preference_choices_match_model(self):
        for key, choice in self.choices.items():
            with self.subTest(key=key):
                _default, allowed = self.prefs[key]
                self.assertIsInstance(allowed, list)
                self.assertEqual(sorted(allowed), sorted(choice))


if __name__ == "__main__":
    unittest.main()
