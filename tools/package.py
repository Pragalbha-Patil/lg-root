"""Stage or package only the files needed to deploy Minimal Home."""

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = (
    "launcher-app/appinfo.json",
    "launcher-app/config.json",
    "launcher-app/icon.png",
    "launcher-app/index.html",
    "launcher-service/config.json",
    "launcher-service/constants.js",
    "launcher-service/model.js",
    "launcher-service/storage.js",
    "launcher-service/json-stream.js",
    "launcher-service/package.json",
    "launcher-service/service.js",
    "launcher-service/services.json",
    "launcher-service/watcher.js",
)
RELEASE_FILES = RUNTIME_FILES + ("LICENSE", "docs/INSTALL.md")


def stage(destination, root=ROOT):
    """Copy the runtime allowlist into a fresh directory, excluding TV state."""
    for name in RUNTIME_FILES:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, target)


def package(destination, root=ROOT):
    """Normalize archive metadata so identical input bytes produce identical output."""
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                for name in sorted(RELEASE_FILES):
                    data = (root / name).read_bytes()
                    entry = tarfile.TarInfo(name)
                    entry.size = len(data)
                    entry.mode = 0o644
                    archive.addfile(entry, io.BytesIO(data))
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_name(destination.name + ".sha256").write_text(
        "%s  %s\n" % (digest, destination.name), encoding="utf-8", newline="\n"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, help="stage runtime files for the installer")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--tag", help="require a release tag matching the configured version")
    args = parser.parse_args(argv)
    try:
        config = json.loads((ROOT / "launcher-app/config.json").read_text(encoding="utf-8"))
        version = config["version"]
        if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
            raise ValueError("version must be MAJOR.MINOR.PATCH")
        if args.tag is not None and args.tag != "v" + version:
            raise ValueError("tag %s does not match config version v%s" % (args.tag, version))
        subprocess.run([sys.executable, str(ROOT / "build_launcher.py"), "--check"],
                       cwd=ROOT, check=True, timeout=60)
        if args.stage:
            if args.stage.exists() and any(args.stage.iterdir()):
                raise ValueError("staging directory must be empty")
            stage(args.stage)
            print("Staged runtime files in %s" % args.stage)
        else:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            destination = args.output_dir / ("minimal-home-v%s.tar.gz" % version)
            package(destination)
            print("Packaged %s (SHA-256 sidecar written)" % destination)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        parser.exit(1, "error: %s\n" % exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
