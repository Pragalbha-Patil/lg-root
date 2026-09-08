#!/usr/bin/env sh
# Minimal Home installer.
# Credential-free by design: the TV address and user come from env vars or an
# ssh config host alias. NEVER hardcode a password or IP here.
#
#   TV_HOST=192.168.1.50  ./install.sh            # deploy + relaunch
#   TV_USER=root ./install.sh                     # override default user (root)
#   ./install.sh --check                          # validate paths, change nothing
#   ./install.sh --no-build                       # skip local build step
#
set -e

TV_USER="${TV_USER:-root}"
TV_HOST="${TV_HOST:-}"
APP_ID="${APP_ID:-org.minimal.home}"
SVC_ID="${SVC_ID:-${APP_ID}.service}"

BASE_DIR="/media/developer/apps/usr/palm"
APP_DIR="${BASE_DIR}/applications/${APP_ID}"
SVC_DIR="${BASE_DIR}/services/${SVC_ID}"

APP_DIR_MISSING=0
SVC_DIR_MISSING=0

shell_quote() {
    printf %s "$1" | sed "s/'/'\\\\''/g"
}

require_host() {
    if [ -z "$TV_HOST" ]; then
        echo "error: TV_HOST not set and no ssh config host given." >&2
        echo "Add an alias to ~/.ssh/config, e.g. 'Host mytv', then run:" >&2
        echo "  TV_HOST=mytv ./install.sh" >&2
        exit 1
    fi
}

check_paths() {
    require_host
    echo "==> checking target paths on ${TV_HOST} (${TV_USER})"
    if ssh "${TV_USER}@${TV_HOST}" "test -d '${APP_DIR}'"; then
        echo "    app dir OK:   ${APP_DIR}"
    else
        APP_DIR_MISSING=1
        echo "    app dir MISSING: ${APP_DIR}"
    fi
    if ssh "${TV_USER}@${TV_HOST}" "test -d '${SVC_DIR}'"; then
        echo "    svc dir OK:   ${SVC_DIR}"
    else
        SVC_DIR_MISSING=1
        echo "    svc dir MISSING: ${SVC_DIR}"
    fi
    if [ "$APP_DIR_MISSING" -eq 0 ] && [ "$SVC_DIR_MISSING" -eq 0 ]; then
        echo "==> all paths present"
    else
        echo "==> run ./install.sh (no --check) to create missing dirs and deploy" >&2
        exit 1
    fi
}

do_build() {
    if [ "${DO_BUILD}" = "0" ]; then
        echo "==> skipping local build (--no-build)"
        return 0
    fi
    echo "==> building launcher"
    python build_launcher.py
}

deploy() {
    require_host
    do_build
    echo "==> creating directories"
    ssh "${TV_USER}@${TV_HOST}" "mkdir -p '$(shell_quote "$APP_DIR")' '$(shell_quote "$SVC_DIR")'"
    echo "==> uploading app (${APP_ID})"
    scp -r launcher-app/. "${TV_USER}@${TV_HOST}:$(shell_quote "$APP_DIR")/"
    echo "==> uploading service (${SVC_ID})"
    scp -r launcher-service/. "${TV_USER}@${TV_HOST}:$(shell_quote "$SVC_DIR")/"
    echo "==> relaunching ${APP_ID}"
    ssh "${TV_USER}@${TV_HOST}" "luna-send -n 1 luna://com.webos.applicationManager/launch '{\"id\":$(shell_quote "$APP_ID")}'" || true
    echo "==> done"
}

DO_BUILD=1
MODE=""
for arg in "$@"; do
    case "$arg" in
        --check) MODE="check" ;;
        --no-build) DO_BUILD=0 ;;
        --help|-h)
            echo "usage: ./install.sh [--check] [--no-build]"
            echo "env:   TV_HOST (required), TV_USER (default root), APP_ID, SVC_ID"
            exit 0
            ;;
    esac
done

if [ "${MODE}" = "check" ]; then
    check_paths
else
    deploy
fi