#!/usr/bin/env sh
# Upload an allowlisted build to an already registered rooted webOS installation.
set -eu

fail() {
    echo "error: $*" >&2
    exit 1
}

DO_BUILD=1
MODE=deploy
for arg in "$@"; do
    case "$arg" in
        --check) MODE=check ;;
        --no-build) DO_BUILD=0 ;;
        --help|-h)
            echo "usage: sh tools/install.sh [--check] [--no-build]"
            echo "env: TV_HOST (SSH alias or hostname), TV_USER (default root), PYTHON (default python)"
            echo "Uploads files and requests launch; does not register Luna services or install boot hooks."
            exit 0
            ;;
        *) fail "unknown option: $arg" ;;
    esac
done

TV_USER=${TV_USER:-root}
TV_HOST=${TV_HOST:-}
PYTHON=${PYTHON:-python}
case "$TV_HOST" in
    ''|-*|*[!a-zA-Z0-9._-]*) fail "set TV_HOST to an SSH alias, hostname, or IPv4 address (use an alias for IPv6)" ;;
esac
case "$TV_USER" in
    ''|-*|*[!a-zA-Z0-9_-]*) fail "invalid TV_USER" ;;
esac
# IDs are embedded in the manifests, generated frontend, and runtime constants.
[ "${APP_ID:-org.minimal.home}" = org.minimal.home ] || fail "APP_ID overrides are unsupported"
[ "${SVC_ID:-org.minimal.home.service}" = org.minimal.home.service ] || fail "SVC_ID overrides are unsupported"
APP_DIR=/media/developer/apps/usr/palm/applications/org.minimal.home
SVC_DIR=/media/developer/apps/usr/palm/services/org.minimal.home.service
REMOTE=${TV_USER}@${TV_HOST}

command -v ssh >/dev/null 2>&1 || fail "ssh is required"
if [ "$MODE" = check ]; then
    echo "Checking target directories on $TV_HOST"
    # Paths are fixed local constants; expand them before sending the command.
    # shellcheck disable=SC2029
    ssh "$REMOTE" "test -d '$APP_DIR' && test -d '$SVC_DIR'"
    echo "Target directories exist (service registration is not checked)."
    exit 0
fi
command -v scp >/dev/null 2>&1 || fail "scp is required"
command -v "$PYTHON" >/dev/null 2>&1 || fail "Python is required; set PYTHON to its executable"
SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR/.."
if [ "$DO_BUILD" -eq 1 ]; then
    "$PYTHON" build_launcher.py
fi

STAGE_DIR=$(mktemp -d)
trap 'rm -rf -- "$STAGE_DIR"' EXIT
trap 'exit 1' HUP INT TERM
# package.py verifies generated output even with --no-build. Stage only shipped
# files so local prefs, usage, icons, or credentials never overwrite TV state.
"$PYTHON" tools/package.py --stage "$STAGE_DIR"
# Paths are fixed local constants; expand them before sending the command.
# shellcheck disable=SC2029
ssh "$REMOTE" "mkdir -p '$APP_DIR' '$SVC_DIR'"
scp -r "$STAGE_DIR/launcher-app/." "$REMOTE:$APP_DIR/"
scp -r "$STAGE_DIR/launcher-service/." "$REMOTE:$SVC_DIR/"
echo "Requesting launch of Minimal Home"
RESPONSE=$(ssh "$REMOTE" "luna-send -n 1 luna://com.webos.applicationManager/launch '{\"id\":\"org.minimal.home\"}'")
printf '%s\n' "$RESPONSE"
printf '%s\n' "$RESPONSE" | "$PYTHON" -c 'import json,sys; sys.exit(0 if json.load(sys.stdin).get("returnValue") is True else 1)'
echo "Upload and launch request succeeded. Running webviews/services may still need restarting; see docs/INSTALL.md."
