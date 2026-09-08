# Repository guide for coding agents

Minimal Home is a launcher for rooted LG webOS TVs. Read
[CONTRIBUTING.md](CONTRIBUTING.md) for workflow,
[architecture](docs/ARCHITECTURE.md) for runtime boundaries, and
[coding standards](docs/CODING_STANDARDS.md) before changing the relevant code.

## Commands

Run from the repository root:

```sh
npm ci --ignore-scripts
npm run format
python build_launcher.py
python tools/check.py
```

The check command is also used in CI. See [testing](docs/TESTING.md) for Node
requirements and coverage gates. npm packages are host-only. It never contacts a
TV. Shell checks require POSIX sh; Linux CI uses `--require-shell`.
Use `python tools/package.py` to prepare a local release archive.

## Source ownership

- UI HTML, CSS, and JavaScript live in `launcher-app/src/`; `build_launcher.py`
  assembles the page. Regenerate and commit `launcher-app/index.html`; never patch it directly.
- Shared preferences, validation, launch parameters, and sorting live in
  `launcher-service/model.js`, also embedded in the page. Rebuild after changing it.
- Shared filesystem helpers belong in `storage.js`; Luna stream framing in `json-stream.js`.
- `launcher-app/config.json` is the config/version source. The generator writes
  `launcher-service/config.json` and stamps `launcher-app/appinfo.json`.
- Relay behavior lives in `launcher-service/service.js`.
- Root watcher behavior lives in `launcher-service/watcher.js`.
- Runtime IDs and filesystem paths belong in `launcher-service/constants.js`.
- Deployment files are allowlisted in `tools/package.py`. Update that list when
  adding an asset needed on the TV.

## Constraints to preserve

- Keep the frontend and relay in their existing ES5 style. The watcher already
  uses modern Node features; do not assume its runtime matches the local Node.
- Use the Python standard library for Python tooling; keep imports free of side effects.
  Keep npm development packages out of TV release payloads.
- Discover inputs from live launch points. Preserve per-port launch parameters,
  but never allow a bookmark's `params.id` to overwrite the target app ID.
- Keep icons app-relative: the file webview cannot load arbitrary absolute paths.
- Keep the runtime config in the service directory: the service jailer cannot
  reliably read the app directory.
- Retain `disableBackHistoryAPI` and the refresh behavior for restored webviews.
- Bound logs, retries, timers, and persisted state. Preserve bypass behavior.
- Build output must be reproducible from public inputs. Personal MRU snapshots
  require explicit `--usage PATH`; restore the default build before a PR.

## Scope and verification

Inspect the existing diff before editing. Keep changes focused and leave unrelated
user work intact. Add behavior-level regressions for bug fixes; do not replace
device quirks without evidence. Runtime tests live in `tests/js/` and exercise
complete scripts with isolated DOM/platform mocks. Preserve per-file coverage gates;
do not add exclusions to meet them. Run the shared check command after changes.

Local development does not imply deployment: do not contact a TV, install boot
hooks, restart services, publish releases, or push changes unless the task
authorizes that action. Do not read or publish `private/` for routine repo work.
Keep credentials, real device addresses, logs, and backups out of tracked files.

In the handoff, explain what changed, which checks passed, and any device behavior
that remains unverified. Avoid hardcoded test counts or personal session state in
this guide.
