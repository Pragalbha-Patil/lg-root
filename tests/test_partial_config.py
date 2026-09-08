import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import build_launcher as bl


class PartialConfigTest(unittest.TestCase):
    def test_partial_ui_retains_defaults_and_builds(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "config.json").write_text(json.dumps({"ui": {"appsPriority": ["custom"]}}))
            with patch.object(bl, "APP_DIR", directory):
                cfg = bl.load_config()
            self.assertEqual(cfg["ui"]["appsPriority"], ["custom"])
            self.assertEqual(cfg["ui"]["inputs"], bl.DEFAULTS["ui"]["inputs"])
            with patch.object(bl, "load_config", return_value=cfg):
                bl.build()

    def test_invalid_fields_fall_back_but_empty_lists_are_respected(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "config.json").write_text(json.dumps({"ui": {"inputs": None, "system": [], "appsPriority": [3]}}))
            with patch.object(bl, "APP_DIR", directory):
                cfg = bl.load_config()
            self.assertEqual(cfg["ui"]["inputs"], bl.DEFAULTS["ui"]["inputs"])
            self.assertEqual(cfg["ui"]["system"], [])
            self.assertEqual(cfg["ui"]["appsPriority"], bl.DEFAULTS["ui"]["appsPriority"])
