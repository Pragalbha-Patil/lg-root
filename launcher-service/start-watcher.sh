#!/bin/sh
# Homebrew Channel runs this hook at boot; it is also safe to run after updates.
set -eu

WATCHER=/media/developer/apps/usr/palm/services/org.minimal.home.service/watcher.js
[ -f "$WATCHER" ] || exit 0

if ps -eo args | awk -v watcher="$WATCHER" '$1 == "node" && $2 == watcher { found = 1 } END { exit !found }'; then
    exit 0
fi

setsid node "$WATCHER" </dev/null >/dev/null 2>&1 &
