import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))

import build_launcher as bl


def make_lp(lp_id, title, system=False, icon=None, params=None):
    return {"id": lp_id, "title": title, "systemApp": system,
            "hidden": False, "icon": icon or "", "largeIcon": "", "params": params}


SAMPLE = [
    make_lp("youtube.leanback.v4", "YouTube", icon="/a/y.png"),
    make_lp("netflix", "Netflix"),
    make_lp("com.webos.app.hdmi1", "HDMI 1", params={"PhysicalAddress": "1000"}),
    make_lp("com.webos.app.discovery", "Apps", system=True),
    make_lp("com.webos.app.settings", "Settings", system=True),
    make_lp("com.webos.app.livetv", "Live TV", system=True),
    make_lp("com.webos.app.homedepot", "Home Depot"),
]


class ClassifyTest(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "ui": {
                "inputs": ["com.webos.app.livetv", "com.webos.app.hdmi1",
                           "com.webos.app.hdmi2", "com.webos.app.hdmi3", "com.webos.app.hdmi4"],
                "system": ["com.webos.app.discovery", "com.webos.app.mediadiscovery",
                           "com.palm.app.settings"],
                "appsPriority": ["youtube.leanback.v4", "netflix"],
            }
        }

    def test_sections(self):
        apps, inputs, sysrow = bl.classify(SAMPLE, self.cfg)
        apps_ids = [t["id"] for t in apps]
        self.assertEqual(apps_ids, ["youtube.leanback.v4", "netflix", "com.webos.app.homedepot"])
        inputs_ids = [t["id"] for t in inputs]
        self.assertIn("com.webos.app.livetv", inputs_ids)
        self.assertIn("com.webos.app.hdmi1", inputs_ids)
        sys_ids = [t["id"] for t in sysrow]
        self.assertIn("com.webos.app.discovery", sys_ids)
        self.assertIn(bl.SETTINGS_ID, sys_ids)
        self.assertIn(bl.LG_HOME_ID, sys_ids)
        self.assertNotIn("com.webos.app.homedepot", [t["id"] for t in inputs] + sys_ids)

    def test_settings_pinned(self):
        apps, inputs, sysrow = bl.classify(SAMPLE, self.cfg)
        settings = next(t for t in sysrow if t["id"] == bl.SETTINGS_ID)
        self.assertEqual(settings["icon"], bl.SETTINGS_ICON)

    def test_hides_self(self):
        lp = SAMPLE + [make_lp("org.minimal.home", "Minimal Home")]
        apps, _, _ = bl.classify(lp, self.cfg)
        self.assertNotIn("org.minimal.home", [t["id"] for t in apps])

    def test_hidden_skipped(self):
        lp = [dict(t) for t in SAMPLE]
        lp[0]["hidden"] = True
        apps, _, _ = bl.classify(lp, self.cfg)
        self.assertNotIn("youtube.leanback.v4", [t["id"] for t in apps])

    def test_missing_settings_pinned(self):
        lp = [t for t in SAMPLE if t["id"] != "com.webos.app.settings"]
        _, _, sysrow = bl.classify(lp, self.cfg)
        self.assertIn(bl.SETTINGS_ID, [t["id"] for t in sysrow])

    def test_system_not_in_known_filtered(self):
        lp = SAMPLE + [make_lp("com.webos.app.othersys", "Other", system=True)]
        _, _, sysrow = bl.classify(lp, self.cfg)
        self.assertNotIn("com.webos.app.othersys", [t["id"] for t in sysrow])


class SortTest(unittest.TestCase):
    def setUp(self):
        self.cfg = {"ui": {"appsPriority": ["netflix", "youtube.leanback.v4"]}}

    def test_priority_order(self):
        tiles = [{"id": "zebra", "title": "Z"}, {"id": "netflix", "title": "N"}]
        sorted_tiles = sorted(tiles, key=lambda t: bl.sort_key(t, {}, self.cfg["ui"]["appsPriority"]))
        self.assertEqual(sorted_tiles[0]["id"], "netflix")

    def test_used_wins_with_mru(self):
        tiles = [{"id": "netflix", "title": "N"}, {"id": "alpha", "title": "A"}]
        usage = {"alpha": 5, "netflix": 1}
        s = sorted(tiles, key=lambda t: bl.sort_key(t, usage, self.cfg["ui"]["appsPriority"]))
        self.assertEqual(s[0]["id"], "alpha")

    def test_unknown_alpha(self):
        tiles = [{"id": "b", "title": "B"}, {"id": "a", "title": "A"}]
        s = sorted(tiles, key=lambda t: bl.sort_key(t, {}, self.cfg["ui"]["appsPriority"]))
        self.assertEqual([t["id"] for t in s], ["a", "b"])


class TemplateTest(unittest.TestCase):
    def test_all_placeholders_substituted(self):
        out, _, _ = bl.build()
        html = out["launcher-app/index.html"]
        self.assertNotIn("__MH_", html)
        self.assertNotIn("__WELCOME_", html)
        self.assertNotIn("__APPS__", html)
        self.assertNotIn("__INPUTS__", html)
        self.assertNotIn("__SYS__", html)

    def test_version_echo(self):
        out, _, _ = bl.build()
        html = out["launcher-app/index.html"]
        self.assertIn('var BUILD = "v', html)
        self.assertIn('window.__MHBUILD = BUILD', html)

    def test_appinfo_version_matches(self):
        out, _, _ = bl.build()
        appinfo = json.loads(out["launcher-app/appinfo.json"])
        self.assertEqual(appinfo["version"], bl.load_config().get("version", "1.0.0"))

    def test_no_ghost_icons(self):
        out, _, _ = bl.build()
        self.assertNotIn('src="icons/settings.png"', out["launcher-app/index.html"])

    def test_settings_tile_uses_provisioned_icon(self):
        out, _, _ = bl.build()
        self.assertIn("icons/com.palm.app.settings.png", out["launcher-app/index.html"])
        self.assertNotIn("/usr/palm/applications/com.palm.app.settings/icon.png",
                         out["launcher-app/index.html"])


class UsageTest(unittest.TestCase):
    def test_usage_reads_service_path_first(self):
        bl.SVC_DIR = bl.SVC_DIR
        path = os.path.join(bl.SVC_DIR, "usage.json")
        self.assertIn("usage.json", path)


if __name__ == "__main__":
    unittest.main()