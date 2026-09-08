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
| `launcher-app/src/` + `launcher-service/model.js` | Self-contained `launcher-app/index.html`, assembled by `build_launcher.py` |
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
| `model.js` | Pure validation, preferences, input classification, launch parameters, and sorting; shared with the frontend |
| `storage.js` | Safe JSON reads, atomic state replacement, and bounded logs |
| `json-stream.js` | Incremental, bounded parsing of chunked Luna subscription output |

Home detection is event-driven. Other watcher work is periodic: icons refresh
every five minutes and system statistics are sampled every five seconds when
enabled. The watcher is not a zero-work idle process. Redirect cooldowns schedule a
retry; reconnections discard stale stream data and timers. Icons are size-checked
before reading and identical bytes are not rewritten. Luna requests have deadlines
and completion guards; the frontend retains only pending requests.

## Persistence

The service directory stores `usage.json`, `prefs.json`, and `.noredirect`.
Usage is a relative launch sequence, renumbered and capped at 60 entries, used
for **recency**, not launch frequency. Pinned/hidden preferences are bounded.
JSON state writes use a temporary file and rename; failed writes preserve the
previous file. Preference updates are serialized in the frontend so rapid edits
cannot arrive at the service out of order.
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
- On webOS 10.3.1, a focused foreground webview can still report
  `document.hidden === true`. Background work checks also use `document.hasFocus()`
  so this stale visibility flag does not prevent live tiles or statistics.
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

Python unit tests cover configuration, rendering, and packaging. Node VM harnesses
execute the relay, watcher, and shared modules with mocked platform APIs. jsdom
runs the complete frontend script against its HTML template with keyboard,
focus, visibility, and service events. The [testing guide](TESTING.md) describes
the enforced coverage gates. These checks need neither root nor a TV. Desktop preview
cannot verify Luna authorization, service jailing, input switching, or remote
key delivery; those need device evidence.
