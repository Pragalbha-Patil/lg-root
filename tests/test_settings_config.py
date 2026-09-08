import copy
import unittest
from unittest.mock import patch

import build_launcher as bl


class SettingsConfigTest(unittest.TestCase):
    def test_removed_settings_stays_removed_after_live_refresh(self):
        cfg = copy.deepcopy(bl.DEFAULTS)
        cfg["ui"]["system"].remove(bl.SETTINGS_ID)
        with patch.object(bl, "load_config", return_value=cfg):
            output, _, _ = bl.build()
        self.assertIn("var SETTINGS_TILE = null;", output["launcher-app/index.html"])
        _, _, system = bl.classify([], cfg)
        self.assertNotIn(bl.SETTINGS_ID, [tile["id"] for tile in system])

    def test_default_settings_fallback_still_present(self):
        output, _, _ = bl.build()
        self.assertIn('var SETTINGS_TILE = {"id": "com.palm.app.settings"', output["launcher-app/index.html"])

    def test_null_settings_is_null_safe_in_frontend(self):
        # rebuild() and the "TV settings" action must never dereference
        # SETTINGS_TILE.id while SETTINGS_TILE is null (settings removed).
        cfg = copy.deepcopy(bl.DEFAULTS)
        cfg["ui"]["system"].remove(bl.SETTINGS_ID)
        with patch.object(bl, "load_config", return_value=cfg):
            output, _, _ = bl.build()
        html = output["launcher-app/index.html"]
        self.assertIn("var SETTINGS_TILE = null;", html)
        self.assertIn("if (SETTINGS_TILE) {", html)
        self.assertIn("if (SETTINGS_TILE) launch(SETTINGS_TILE.id, null)", html)
        self.assertNotIn("; launch(SETTINGS_TILE.id, null)", html)