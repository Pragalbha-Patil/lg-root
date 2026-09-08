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
        self.assertIn('"settingsTile": null', output["launcher-app/index.html"])
        _, _, system = bl.classify([], cfg)
        self.assertNotIn(bl.SETTINGS_ID, [tile["id"] for tile in system])

    def test_default_settings_action_metadata_still_present(self):
        output, _, _ = bl.build()
        self.assertIn('"settingsTile": {"id": "com.palm.app.settings"', output["launcher-app/index.html"])
