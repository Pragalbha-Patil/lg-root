# Architecture

## Build and runtime boundaries

`build_launcher.py` runs on the contributor's computer. It reads
`launcher-app/config.json` and a sample `tiles.json`, classifies apps and inputs,
and renders an immediately usable fallback page. The TV does not run Python to
start the launcher.

The web app (`org.minimal.home`) runs in a webOS webview. It calls the Node relay
(`org.minimal.home.service`) over Luna for live tiles, launches, preferences,
the LG Home bypass, and system statistics. The root watcher is a separate,
long-running process: it subscribes to foreground changes, launches Minimal Home
when stock Home appears, provisions icons, and samples system statistics.

## Sources and generated files

| Source | Output or consumer |
| --- | --- |
| `build_launcher.py` template | `launcher-app/index.html` |
| `launcher-app/config.json` | Generated `launcher-service/config.json` |
| Config version | `appinfo.json` version and embedded build string |
| `launcher-app/tiles.json` | Static fallback tiles |
| Explicit `--usage PATH` | Optional personal fallback ordering |
| `launcher-service/constants.js` | Shared service/watcher IDs and paths |

The generated page and service config are committed. The manifest is maintained
directly except for its generated version. `python build_launcher.py --check`
reports drift without writing files. Default builds ignore local usage snapshots.

## Runtime responsibilities

| Component | Responsibilities |
| --- | --- |
| Frontend | Rendering, focus, search, menus, refresh, and Luna requests |
| `service.js` | `getTiles`, `launchApp`, `openLGHome`, `getPrefs`, `setPrefs`, `getSystemStats` |
| `watcher.js` | Foreground subscription/reconnects, redirect retries, icon copies, stats sampling |
| `constants.js` | App/service IDs, install locations, state and log paths |

Home detection is event-driven. Other watcher work is periodic: icons refresh
every five minutes and system statistics are sampled every five seconds when
enabled. The watcher is not a zero-work idle process.

## Persistence

The service directory stores `usage.json`, `prefs.json`, and `.noredirect`.
Usage is a monotonically increasing launch sequence, capped at 60 entries, used
for **recency**, not launch frequency. Pinned/hidden preferences are bounded.
The bypass stores an expiry timestamp for ten minutes.

The watcher writes icons inside the app's `icons/` directory and a temporary
statistics sample at `/tmp/minhome-stats.json`. Logs are
`/tmp/minhome-svc.log` and `/tmp/minhome-watch.log`. Files under `/tmp` are
ephemeral across reboot. Deployment excludes all of this device state.

## webOS constraints

These constraints come from project device observations, including webOS
10.3.1. Treat them as evidence for that environment, not universal platform guarantees.

- A file-based webview cannot load arbitrary absolute icon paths. The root
  watcher copies icons into the app, and the relay returns relative paths.
- The dev-mode service jailer cannot reliably read files in the app directory.
  The generated service-local config is intentional.
- Background webviews can be purged after a short delay. Refresh on foreground
  return; do not assume in-memory state survived another app.
- `disableBackHistoryAPI: true` lets the app handle Back rather than delegating
  it to a platform exit/history dialog.
- Input tiles come from launch points and bookmark metadata. Preserve
  `PhysicalAddress`/`value` and other allowed per-port parameters, while
  preventing bookmark `params.id` from replacing the target app ID.
- The foreground subscription uses
  `com.webos.applicationManager/getForegroundAppInfo`, not `getForegroundApp`.
- Changed files do not necessarily replace already-running webview, relay, or
  watcher processes. See [installation](INSTALL.md) for verification.

The input classifier exists in Python and JavaScript because both the static
fallback and live tiles need it. Keep their behavior aligned through regression
tests when changing classification.

## Test boundary

Python unit tests cover configuration and rendering. Node VM harnesses exercise
frontend fragments, the relay, and the watcher with mocked platform APIs.
They check logic and failures without needing root or a TV. Desktop preview
cannot verify Luna authorization, service jailing, input switching, or remote
key delivery; those need device evidence.
