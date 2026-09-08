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
- **Webviews are purged 10–15 s after backgrounding** (WAM flags
  `--min-delay-to-purge-after-backgrounded-in-seconds=10 --max-...=15`). Never trust backgrounded
  webview state — that's why `refresh()` re-fetches from the service on `visibilitychange`/`focus`.
  Kill a renderer with `pkill -f 'app-id=<id>'` (match against `ps aux | grep 'app-id='`; the
  browser process carries no app-id). A palette/`app-id` case: one `pkill` round may leave 1 renderer
  that SAM relaunched — loop until zero before fresh-launch.
- **Luna API reality check (webOS 10.3.1):** `getForegroundAppInfo` exists and supports
  `subscribe`; there is NO `getForegroundApp`. `com.webos.notification/{getStatus,getNotifications}`,
  `settings/getSettings`, `db8/listKinds`, `setOrder`/`moveLaunchPoint` do not exist / do nothing on
  this build. Don't design against them.
- **Dynamic service reload:** `org.minimal.home.service` runs on-demand under Luna. To pick up new
  `service.js`, kill the service's node PID; the next bus call relaunches it from disk. Paths come
  from `constants.js` (authoritative): app `/media/developer/apps/usr/palm/applications/org.minimal.home`,
  service `/media/developer/apps/usr/palm/services/org.minimal.home.service`.
- **Luna testing:** `luna-send -n 1 -f 'luna://<service>/<method>' '<json>'`. Screen capture for
  on-device verification: `luna://com.webos.service.capture/executeOneShot` with
  `{"path":"/tmp/x.png","method":"DISPLAY","format":"PNG"}`. Subscribe for streaming replies:
  `luna-send -n 1000000 -f 'luna://com.webos.applicationManager/getForegroundAppInfo' '{"subscribe":true}'`
  (how `watcher.js` detects Home appearing).

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

## Rooted webOS platform facts (this TV — all verified on device)

**Device/root.** webOS 10.3.1 "starfish", kernel 5.4.268-294.24.papikonda.2 (aarch64), rooted via
webosbrew (RootMyTV; `telnetd`/`sshd` + init hooks). Node + `webos-service` are present on the TV
(`/usr/bin/node`, `/usr/lib/node_modules/webos-service`), as are `python3` (`/usr/bin/python3`, 3.10)
and `sqlite3`.

**Filesystem.** `/` is a squashfs, ~100% full; `/etc` and `/usr` are read-only overlays (their files
are date-stamped `Apr 6 2011` — image build time, a reliable read-only marker). Consequences:
- `/etc/hosts` is NOT directly editable. Block trick: build `/tmp/hosts-adblock`, then
  `mount --bind /tmp/hosts-adblock /etc/hosts` — applies instantly (glibc `nss_files` picks it up).
- `/tmp` is tmpfs and is wiped on every reboot: all `/tmp/minhome-*.log` files, the hosts-block
  source file, and any bind-mounted appinfo fallbacks vanish. Persist durable state under
  `/media/developer` (writable apps partition) — e.g. `/media/developer/tv-backup`,
  `/media/developer/tv-block`.
- Reboot: `luna://com.webos.service.sleep/shutdown/machineReboot {"reason":"remoteKey"}`.

**Boot hooks.** Any executable under `/var/lib/webosbrew/init.d/` runs at boot (run-parts). Current
hooks: `50-block-ads`, `60-hide-apps`, `70-watchhome`, `71-bootlaunch`. **Write them as LF only** —
CRLF silently breaks the hook at boot; normalize with `tr -d '\r'` and gate on `sh -n`. Revert =
delete the file + reboot (or unbind for the session). `70-watchhome` waits for the luna bus
(`getForegroundAppInfo` polling) before spawning the watcher with `setsid ... </dev/null >/dev/null
2>&1 &` + `disown` (plain nohup dies when the SSH session ends).

**SAM (system app manager).** `sam.service`; `systemctl restart sam` reloads appinfo (~30–60 s).
Hiding an app = bind-mount a rewritten `appinfo.json` (`"visible": false`) over the live install then
restart sam; if `listApps` still reports `visible: true`, a running WAM renderer is pinning the old
appDesc — `pkill -f 'app-id=<id>'` and re-list. Backup first: `/media/developer/tv-backup/`
(`appinfo-system/appinfo.json` = LG Channels' real install under `/media/system/apps/...`;
`homelaunchpoints-backup/qcard-server.json`; `blockedAppList-backup/IND.json` +
`blockedSystemAppList-backup/IND.json`; `admanager-cache/` = 79 pulled ad assets). Store apps live
under `/media/cryptofs/apps/usr/palm/applications/` (netflix, amazon, youtube, hotstar, zee5...).
Real removal is permanent only via `com.webos.appInstallService/remove {"id": ...}` — moving the app
dir out of the scan path does NOT stick (SAM re-adds within ~15 s). Tile order policy:
`/var/palm/customization/launchpoints/<COUNTRY>/` + `applist_by_policy.json`.

**WAM (webviews).** Remote debugging on `--remote-debugging-port=9998` (`/var/lib/wam/DevToolsActivePort`);
renderers carry `--app-id=` in `ps aux`, the browser process doesn't. Useful WAM flags seen live:
`--user-agent-suffix=SmartTV`, `--no-sandbox`, `--disk-cache-size=52428800`, purge delays 10/15 s.

**Stock Home app.** `com.webos.app.home` is Flutter: `flutter-client -i com.webos.app.home` running
`/usr/palm/applications/com.webos.app.home/lib/libapp.so` (full appDesc passes on argv). Kill the
PID → ~10 s blank → fresh reload. Prefs DB: `/var/preferences/com.webos.app.home/prefsDB.sl`
(sqlite, one `data(key,value)` table). Home shelves are configured in
`data/flutter_assets/assets/mock/shelf/shelf_list_mock_data.json` (11 shelves incl.
`HOME_SH_RECOMMENDED`/`HOME_SH_EDITORSPICK`, served by SDP/tlamp backends) — "Now Streaming" and the
recommendation shelves die with `contentRecommendation=off` + hosts-blocking.

**Ads/promotions knobs (official settings API).** `luna://com.webos.service.settings/getSystemSettings`
/ `setSystemSettings` with `{"category":...,"key":...}` / `{"category":...,"settings":{...}}`. Switch
set verified on this TV: `general` → `homePromotion`, `screenSaverAd`, `adCookie`, `customizedAd`,
`sportsAlarm`; `option` → `livePromotion`, `webOSPromotionVideo`, `miracastOverlayAdRecovery`;
`other` → `contentRecommendation`. Also `general` `powerOnScreen` (`todays`|Home|Recent Input),
`homeAutoLaunch`. `admanager` (`/usr/sbin/admanager`, child of `ls-hubd`) drives promotion banners
via `/mnt/lg/cmn_data/admanager/{homePromotion,cache,cookie,tmpData}` (`baseInfo.tmp` carries the
ad-slot list; server `in.ad.lgsmartad.com`). Hosts-blocked domains (also in `50-block-ads`):
`info.lgsmartad.com`, `adinfo.lgsmartad.com`, `lgadsp.lgtvcommon.com`, `in.ad.lgsmartad.com`,
`ad.lgsmartad.com`.

**On-device state as of last session.** Hidden (visible:false bind-mounts, re-applied by `60-hide-apps`):
`com.webos.app.lgchannels`, `com.webos.app.sportsteamsettings`, `com.webos.app.lifeonscreen`,
`amazon.alexa.view`, `com.webos.app.renewupdate`. Removed: `shortcutcopilot`, `epoxyaisports`,
`com.twin.app.gamingportal`. Ad settings off + hosts block active + homePromotion flag `false`.
Post-reboot proof: foreground `org.minimal.home`, watcher auto-running (`/media/developer/tv-block/hook-boot.log`).

## Luna service registration (the relay pattern)

The relay registers the way all root-app systems do (hbchannel, litefin, safeupdate): via the
dev-mode ls2 dirs `/var/luna-service2-dev/{manifests.d,services.d,api-permissions.d,roles.d,client-permissions.d}`
plus `/var/luna-service2/client-permissions.d`. Least-privilege split that works: the **app** client
perm is `{"org.minimal.home-*": ["public"]}` (the webview only needs `public`);
the **service** client perm is `{"org.minimal.home.service*":
["public","applications","applications.launch","applications.query","applications.internal"]}` —
that's what lets `service.js` call SAM's `listLaunchPoints`/`listApps`/`launch`. Without those
groups the app's own `listLaunchPoints` call fails with "Denied method call listLaunchPoints".

## Deploying to the TV

Use `tools/install.sh` or manual `scp` (README "Install on the TV"). Paths:

- App: `scp -r launcher-app/. root@<TV>:/media/developer/apps/usr/palm/applications/org.minimal.home/`
- Service: `scp -r launcher-service/. root@<TV>:/media/developer/apps/usr/palm/services/org.minimal.home.service/`

Then restart the webview + reload the dynamic service as described above.

MRU order: the service writes `usage.json` next to `service.js` on the TV (counter-based, 60-entry
cap, evicts least-used). Before a build, `pull usage.json` into `launcher-app/` so
`build_launcher.py` bakes the current MRU order into the static grid (no reshuffle flash on load);
a missing file is fine — it falls back to `config.json` priority/title order.