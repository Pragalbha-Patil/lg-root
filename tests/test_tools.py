"""Host tooling regressions: deterministic builds, packages, and installer failures."""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import build_launcher as bl
from tools import check, package

ROOT = Path(__file__).resolve().parents[1]
SHELL = check.find_shell()


class ConfigValidationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config.json"
        self.patcher = patch.object(bl, "APP_DIR", str(self.root))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def write_config(self, value):
        self.config.write_text(json.dumps(value), encoding="utf-8")

    def test_partial_config_inherits_defaults_without_mutating_them(self):
        defaults = copy.deepcopy(bl.DEFAULTS)
        self.write_config({"ui": {"system": []}, "header": {"text": "Hello"}})
        config = bl.load_config()
        self.assertEqual(config["ui"]["system"], [])
        self.assertEqual(config["ui"]["appsPriority"], defaults["ui"]["appsPriority"])
        self.assertEqual(config["header"]["brand"], defaults["header"]["brand"])
        config["ui"]["appsPriority"].clear()
        self.assertEqual(bl.DEFAULTS, defaults)

    def test_invalid_config_fails_instead_of_using_defaults(self):
        for value in ([], {"version": "../bad"}, {"header": []},
                      {"header": {"text": None}}, {"ui": {"system": "all"}},
                      {"ui": {"appsPriority": [1]}}):
            with self.subTest(value=value):
                self.write_config(value)
                with self.assertRaises(ValueError):
                    bl.load_config()
        self.config.write_text("{broken", encoding="utf-8")
        with self.assertRaises(ValueError):
            bl.load_config()

    def test_missing_config_returns_independent_defaults(self):
        config = bl.load_config()
        config["ui"]["system"].clear()
        self.assertTrue(bl.DEFAULTS["ui"]["system"])


class BuildInputsTest(unittest.TestCase):
    def test_personal_state_is_only_loaded_explicitly(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "usage.json"
            path.write_text('{"netflix": 42}', encoding="utf-8")
            with patch.object(bl, "SVC_DIR", temp):
                self.assertEqual(bl.load_usage(), {})
                self.assertEqual(bl.load_usage(path), {"netflix": 42})
                output, _, usage = bl.build(usage_path=path)
                self.assertEqual(usage, {"netflix": 42})
                page = output["launcher-app/index.html"]
                self.assertLess(page.index('data-id="netflix"'), page.index('data-id="youtube.leanback.v4"'))

    def test_invalid_or_missing_explicit_usage_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "usage.json"
            with self.assertRaises(FileNotFoundError):
                bl.load_usage(path)
            for value in ([], {"netflix": True}, {"netflix": -1}, {"netflix": "2"}):
                with self.subTest(value=value):
                    path.write_text(json.dumps(value), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        bl.load_usage(path)

    def test_version_override_stamps_all_outputs(self):
        output, _, _ = bl.build("2.3.4")
        self.assertEqual(json.loads(output["launcher-app/appinfo.json"])["version"], "2.3.4")
        self.assertEqual(json.loads(output["launcher-service/config.json"])["version"], "2.3.4")
        self.assertIn('var BUILD = "v2.3.4"', output["launcher-app/index.html"])
        with self.assertRaises(ValueError):
            bl.build('1.0.0";bad')


class PackagingTest(unittest.TestCase):
    def test_reproducible_archive_allowlist_and_checksum(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "source"
            for name in package.RELEASE_FILES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(("fixture: " + name).encode())
            (root / "launcher-service/prefs.json").write_text('{"private":true}', encoding="utf-8")
            first, second = Path(temp) / "first.tar.gz", Path(temp) / "second.tar.gz"
            package.package(first, root)
            for name in package.RELEASE_FILES:
                os.utime(root / name, (100000, 100000))
            package.package(second, root)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with tarfile.open(first) as archive:
                self.assertEqual(set(archive.getnames()), set(package.RELEASE_FILES))
                for entry in archive:
                    self.assertEqual(entry.mtime, 0)
                    self.assertEqual(entry.mode, 0o644)
                    self.assertEqual(archive.extractfile(entry).read(), (root / entry.name).read_bytes())
            checksum = first.with_name(first.name + ".sha256").read_text().split()[0]
            self.assertEqual(checksum, hashlib.sha256(first.read_bytes()).hexdigest())
            staged = Path(temp) / "staged"
            package.stage(staged, root)
            actual = {p.relative_to(staged).as_posix() for p in staged.rglob("*") if p.is_file()}
            self.assertEqual(actual, set(package.RUNTIME_FILES))

    def test_mismatched_tag_fails_before_build_or_packaging(self):
        with patch.object(package.subprocess, "run") as run:
            with self.assertRaises(SystemExit) as error:
                package.main(["--tag", "v999.0.0"])
            self.assertEqual(error.exception.code, 1)
            run.assert_not_called()

    def test_stale_build_prevents_packaging(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "dist"
            with patch.object(package.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "build")):
                with self.assertRaises(SystemExit):
                    package.main(["--output-dir", str(destination)])
            self.assertFalse(destination.exists())


@unittest.skipUnless(SHELL, "POSIX sh is required for installer regression tests")
class InstallerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "calls.log"
        self.env = dict(os.environ, TV_HOST="example-tv", TV_USER="root",
                        PYTHON=Path(sys.executable).as_posix(), MH_CALL_LOG=self.log.as_posix(),
                        MH_RESPONSE='{"returnValue":true}', MH_SSH_EXIT="0", MH_SCP_EXIT="0")
        self.env.pop("APP_ID", None)
        self.env.pop("SVC_ID", None)
        self.env["PATH"] = os.pathsep.join((str(self.bin), str(Path(SHELL).parent), self.env["PATH"]))
        self.stub("ssh", 'printf "ssh\\n" >> "$MH_CALL_LOG"\nprintf "%s\\n" "$@" >> "$MH_CALL_LOG"\n'
                  'if [ "$MH_SSH_EXIT" != 0 ]; then exit "$MH_SSH_EXIT"; fi\n'
                  'case "$*" in *luna-send*) printf "%s\\n" "$MH_RESPONSE";; esac\n')
        self.stub("scp", 'printf "scp\\n" >> "$MH_CALL_LOG"\nprintf "%s\\n" "$@" >> "$MH_CALL_LOG"\n'
                  'exit "$MH_SCP_EXIT"\n')

    def stub(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\nset -eu\n" + body, encoding="utf-8", newline="\n")
        path.chmod(0o755)

    def install(self, *args):
        # Run outside the checkout to catch accidental reliance on cwd.
        return subprocess.run([SHELL, (ROOT / "tools/install.sh").as_posix(), *args],
                              cwd=self.root, env=self.env, capture_output=True,
                              text=True, encoding="utf-8", timeout=30)

    def test_help_and_unknown_arguments_do_not_contact_tv(self):
        self.env.pop("TV_HOST")
        self.assertEqual(self.install("--help").returncode, 0)
        self.assertNotEqual(self.install("--typo").returncode, 0)
        self.assertFalse(self.log.exists())

    def test_invalid_destinations_and_id_overrides_are_rejected(self):
        for host in ("-oProxyCommand=bad", "tv;echo bad", "user@tv", ""):
            with self.subTest(host=host):
                self.env["TV_HOST"] = host
                self.assertNotEqual(self.install("--check").returncode, 0)
        self.env["TV_HOST"] = "example-tv"
        self.env["APP_ID"] = "other.app"
        self.assertNotEqual(self.install("--check").returncode, 0)
        self.assertFalse(self.log.exists())

    def test_check_only_uses_read_only_ssh(self):
        result = self.install("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text()
        self.assertIn("test -d", calls)
        self.assertNotIn("scp", calls)
        self.assertNotIn("mkdir", calls)

    def test_upload_sends_valid_launch_json(self):
        result = self.install("--no-build")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        command = next(line for line in self.log.read_text().splitlines() if "luna-send" in line)
        payload = command.split("'", 2)[1]
        self.assertEqual(json.loads(payload), {"id": "org.minimal.home"})
        self.assertEqual(self.log.read_text().splitlines().count("scp"), 2)

    def test_upload_failure_prevents_launch(self):
        self.env["MH_SCP_EXIT"] = "1"
        result = self.install("--no-build")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("luna-send", self.log.read_text())

    def test_remote_and_luna_failures_propagate(self):
        self.env["MH_SSH_EXIT"] = "255"
        self.assertNotEqual(self.install("--check").returncode, 0)
        self.env["MH_SSH_EXIT"] = "0"
        for response in ('{"returnValue":false}', 'not json'):
            with self.subTest(response=response):
                self.env["MH_RESPONSE"] = response
                self.assertNotEqual(self.install("--no-build").returncode, 0)
                self.assertIn("luna-send", self.log.read_text())


if __name__ == "__main__":
    unittest.main()
