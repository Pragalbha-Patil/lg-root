import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import build_launcher as bl


class UsageValidationTest(unittest.TestCase):
    def test_bad_entries_do_not_break_sorting(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "usage.json").write_text(json.dumps({
                "recent": 5, "old": 1, "text": "oops", "null": None,
                "bool": True, "negative": -1, "infinite": float("inf"),
                "nan": float("nan")
            }))
            with patch.object(bl, "SVC_DIR", directory):
                usage = bl.load_usage()
            self.assertEqual(usage, {"recent": 5, "old": 1})
            tiles = [{"id": key, "title": key} for key in ["text", "old", "recent"]]
            ordered = sorted(tiles, key=lambda tile: bl.sort_key(tile, usage, []))
            self.assertEqual([tile["id"] for tile in ordered], ["recent", "old", "text"])
