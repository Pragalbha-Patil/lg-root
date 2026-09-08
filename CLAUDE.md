# CLAUDE.md

Agent guide for **webos-minimal-home** — a minimalist, ad-free home screen replacement for rooted
LG webOS TVs. It replaces stock Home with a single screen: your apps, your inputs (detected live
from the TV), and a clock. Runs in webOS developer mode on-device.

## Architecture in one paragraph

`build_launcher.py` (dev machine only) renders `launcher-app/index.html` + stamps `appinfo.json`.
On the TV, the webOS web app (`org.minimal.home`) talks to the Node relay service
(`org.minimal.home.service`) over Luna bus (`luna://org.minimal.home.service`). `service.js`
serves `getTiles` (live tile list + prefs), `launchApp`, `openLGHome`, and MRU persistence; a
separate `watcher.js` redirects stock `com.webos.app.home` to this launcher (10-minute bypass via
`.noredirect`).

## Repository layout

```
webos-minimal-home/
├── build_launcher.py        # GENERATES index.html/appinfo.json; not run on TV
├── launcher-app/            # the on-screen web app
│   ├── appinfo.json         # manifest (version stamped by build)
│   ├── config.json          # version + header + ui.system allowlist + ui.appsPriority
│   ├── tiles.json           # sample launch-point snapshot for offline/local builds
│   ├── spatial-nav.js       # DEPRECATED — do not use; launcher logic is baked in
│   └── index.html           # GENERATED — commit it, never hand-edit
├── launcher-service/        # Node relay service + redirect watcher
│   ├── constants.js         # single source: ids, mount paths, log paths
│   ├── service.js           # getTiles / launchApp / openLGHome + MRU usage
│   ├── watcher.js           # stock Home → Minimal Home redirect daemon
├── tests/test_build_launcher.py  # unittest suite (21)
├── tools/install.sh         # deploy helper (scp to the TV)
├── private/                 # GIT-IGNORED: credentials, personal tooling — NEVER commit
```

## Build & CI gate (MUST be green before committing/pushing)

```
python build_launcher.py                 # regenerate app files
python build_launcher.py --check         # CI staleness gate (fails if outputs drifted)
python -m unittest discover -s tests     # 21 tests
node --check launcher-service/service.js   # also watcher.js, constants.js
```

- **Never hand-edit `launcher-app/index.html`** — edit `build_launcher.py` and rebuild. The page
  is committed so the repo is self-contained and drift is caught by `--check`.
- Keep `launcher-app/config.json` in sync any time `build_launcher.py`'s `DEFAULTS` change: the
  service reads the **same** file at runtime, so bake-time and live behavior can't diverge.
- Version is single-sourced in `config.json`; `build_launcher.py` stamps `appinfo.json` + the
  `__MH_VERSION__` build string from it.

## Coding standards

- **JS (relay service):** ES5 style — `var`, `function`, callbacks (the `webos-service` module is
  callback-based), 4-space indent, single quotes. JSON-string values keep double quotes.
- **Python (build):** stdlib only (`json`, `re`, `argparse`, `html`, `unittest`). `build_launcher.py`
  must be importable without side effects at import (tests import it). No third-party deps.
- **Tests:** unit-test any new classify/build logic in `tests/test_build_launcher.py`. Keep the
  suite green; add fixtures for edge cases (dynamic inputs, params propagation, generated-artifact
  staleness).
- **Logging:** `service.js` appends JSON lines to `/tmp/minhome-svc.log` via `log()`; the log
  rotates itself beyond 100 KB (`fs.WriteFileSync` caps it). No unbounded log growth (see issues
  #5/#6). The watcher logs to `/tmp/minhome-watch.log`.
- **Error handling:** always respond `{ returnValue: false, errorText: ... }` on failures; success
  responses carry `returnValue: true`. Log a structured `log({ m: ..., err: ... })` line.
- **Comments:** explain *why* (especially webOS quirks), not *what*. No filler comments.
- **No secrets in the repo:** credentials, TV IPs, personal scripts, debug dumps go in `private/`
  (git-ignored). See `SECURITY.md`.

## webOS runtime rules (learned on device — do not "fix")

- **file:// webview blocks absolute icon paths.** The watcher copies every launch point's icon into
  `org.minimal.home/icons/<id>.png`; `getTiles` returns `ICONS_PREFIX + id + '.png'` so the app can
  render them. Don't switch icon serving to absolute filesystem paths.
- **Stale webview sessions:** after pushing app files, the running webview keeps old JS. Restart it:
  `systemctl restart webapp-mgr` (or relaunch the app) to load new `index.html`. The screensaver
  also purges/backgrounds the launcher webview, so keep long test waits out-of-band.
- **Dynamic service reload:** `org.minimal.home.service` runs on-demand under Luna. To pick up new
  `service.js`, kill the service's node PID; the next bus call relaunches it from disk. Paths come
  from `constants.js` (authoritative): app `/media/developer/apps/usr/palm/applications/org.minimal.home`,
  service `/media/developer/apps/usr/palm/services/org.minimal.home.service`.
- **Luna testing:** `luna-send -n 1 -f 'luna://<service>/<method>' '<json>'`. Screen capture for
  on-device verification: `luna://com.webos.service.capture/executeOneShot` with
  `{"path":"/tmp/x.png","method":"DISPLAY","format":"PNG"}`.

## Inputs (issue #24 — the hard-won rules)

- **Inputs are NEVER hardcoded.** The system publishes a launch point per connected input
  (bookmarks like `com.webos.app.hdmi2` with per-port params, plus built-in `com.webos.app.livetv`);
  a port disappears when unplugged and reappears when replugged. Classify live from
  `listLaunchPoints`: `lptype === 'bookmark'` OR the port namespace
  `com.webos.app.(livetv|hdmi|av|scart|dp|usbc)*` (same regex in `service.js` `INPUT_ID_RE` and
  `build_launcher.py` `MH_INPUT_RE`). `getTiles` returns the Inputs group separately from apps.
- **Never let bookmark params clobber the app id.** Input-bookmark `params` contain a marker
  `id: "uniqueId"`. When copying params into a launch payload (frontend `launch()` *and* service
  `launchApp`), **skip `k === 'id'`** — otherwise the payload launches `"uniqueId"` and appmgr
  answers `not exist`.
- **Pass the per-port params.** `PhysicalAddress` + `value` from the launch point must reach
  `applicationManager/launch` or the input app engages nothing (black screen). `launchApp` merges
  the *live* launch-point params so even stale baked tiles switch correctly.
- This is the stock Home approach: launching the input app makes `inputcommon` fire
  `com.webos.service.utp.extinputs/switchExternalInput` → broadcast → `extinputs.hdmi`. Nothing
  extra is needed for the switch itself.

## System-app allowlist

Only system (`com.webos.app.*`) apps listed in `config.json` `ui.system` become tiles — `service.js`
(`ALLOW_SYSTEM`) and the build agree via the shared config file. `com.webos.app.livetv` is exempt
(it's input-classified, not a system tile). `launcher-app/config.json` has no `inputs` key by design.

## Deploying to the TV

Use `tools/install.sh` or manual `scp` (README "Install on the TV"). Paths:

- App: `scp -r launcher-app/. root@<TV>:/media/developer/apps/usr/palm/applications/org.minimal.home/`
- Service: `scp -r launcher-service/. root@<TV>:/media/developer/apps/usr/palm/services/org.minimal.home.service/`

Then restart the webview + reload the dynamic service as described above.