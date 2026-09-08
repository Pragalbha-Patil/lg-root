# Minimal Home — LG webOS Launcher

A minimalist, ad-free home screen replacement for **rooted LG webOS TVs** (developed on webOS 23).

No recommendations rows. No promotional tiles. No carousel of content you will never watch. Just
**your apps**, **your inputs**, and a clock — on a near-black, OLED-friendly background.

```
┌────────────────────────────────────────────────────────────────────┐
│  WELCOME  Minimal Home                          ⚙ Settings 10:24 PM│
│                                                          Tuesday   │
│                                                                     │
│  APPS                                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  ▶ YouTube│ │  N Netflix│ │ P. Prime │ │ S Stremio│ │ J Jellyfin│ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                                                                     │
│  INPUTS                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │ TV  Live │ │ HDMI 1   │ │ HDMI 2   │ │ HDMI 3   │               │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘               │
│                                                                     │
│  SYSTEM                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                              │
│  │ Apps     │ │ Media    │ │ Settings │ LG Home                     │
│  └──────────┘ └──────────┘ └──────────┘                              │
└────────────────────────────────────────────────────────────────────┘
```

## Features

- **Ad-free & distraction-free** — only what you actually use, sorted three ways:
  - **Most recently used** apps first (persisted to disk on the TV, capped at 60 entries)
  - Then a curated priority list, then the rest alphabetically
- **Live tile refresh** — app list re-fetches from the TV when the launcher regains focus, so
  newly installed apps appear without a rebuild
- **Remote-friendly** — full D-pad spatial navigation, auto-focus on boot
- **No polling watcher** — an event-driven service reacts instantly to foreground changes and
  redirects stock LG Home to Minimal Home
- **Built-in bypass** — an "LG Home" tile lets you temporarily reach the stock launcher
  (10-minute hold-off, so it doesn't immediately bounce you back)
- **Static-configured, dynamic-runtime** — the UI works even before the relay service answers,
  then upgrades in place to the live tile set
- **Configurable greeting** — tweak the header text without touching code (`launcher-app/config.json`)

## Contents

- [Requirements](#requirements)
- [Build](#build)
- [Install on the TV](#install-on-the-tv)
- [Configuration](#configuration)
- [How it works](#how-it-works)
- [Repository layout](#repository-layout)
- [Development](#development)
- [Known limitations](#known-limitations)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)

## Requirements

- A **rooted** LG webOS TV with SSH access (see the
  [webOS Homebrew project](https://www.webosbrew.org) — Homebrew Channel, root tooling).
  Developed and tested on **webOS 23**.
- Python 3.7+ to build the launcher page.
- Everything else runs **on the TV**: the app is a plain webOS web app, the relay service and
  watcher are Node.js (webOS ships Node).

## Build

```sh
git clone https://github.com/Pragalbha-Patil/lg-root.git
cd lg-root
python build_launcher.py
```

This reads `launcher-app/tiles.json` (a sample launch-point snapshot) and `launcher-app/config.json`
and generates `launcher-app/index.html`. The generated page is the app's entry point
(`main` in `appinfo.json`), so the whole `launcher-app/` folder is what runs on the TV.

> **Note:** the launcher re-fetches the real, live tile list over Luna from the relay service when
> it starts. `tiles.json` is only the static fallback that renders instantly on boot — it does not
> need to match your TV exactly. To snapshot your own TV's launch points, grab the output of:

```sh
luna-send -n 1 luna://com.webos.applicationManager/listLaunchPoints '{}'
```

## Install on the TV

No credentials or deployment script are bundled in this repository (your TV's address,
SSH credentials and personal tooling stay out of the public tree). Deploy via plain
`scp`/`ssh` as `root` on your rooted TV:

```sh
# 1. Build the app locally
python build_launcher.py

# 2. Upload the app
scp -r launcher-app root@<TV-IP>:/media/developer/apps/usr/palm/applications/org.minimal.home/

# 3. Upload the relay service
scp -r launcher-service root@<TV-IP>:/media/developer/apps/usr/palm/services/org.minimal.home.service/

# 4. Launch it
ssh root@<TV-IP> "luna-send -n 1 luna://com.webos.applicationManager/launch '{\"id\":\"org.minimal.home\"}'"
```

To make Minimal Home the launcher that opens instead of stock LG Home, start the redirect
watcher once and have it autostart at boot (e.g. from your root boot-hook script — webOS Homebrew
users typically have one already):

```sh
# on the TV, after a boot hook is in place:
setsid node /media/developer/apps/usr/palm/services/org.minimal.home.service/watcher.js \
  </dev/null >/dev/null 2>&1 &
```

## Configuration

### Header greeting — `launcher-app/config.json`

```json
{
    "header": {
        "text": "Welcome",
        "brand": "Minimal Home"
    }
}
```

`text` is rendered small-and-regular, `brand` is rendered bold. Rebuild and redeploy to apply.

### System app allowlist — `launcher-service/service.js`

Only these system (non-third-party) apps are exposed as tiles. Everything else from the TV
(apps you installed, HDMI bookmarks) is shown automatically.

```js
var ALLOW_SYSTEM = ['com.webos.app.livetv',
    'com.webos.app.hdmi1', 'com.webos.app.hdmi2', 'com.webos.app.hdmi3', 'com.webos.app.hdmi4',
    'com.webos.app.mediadiscovery', 'com.webos.app.discovery'];
```

Add a `com.webos.app.*` id here if you want a particular system app to appear as a tile.

### Most-recently-used ordering

`launcher-service/service.js` records every successful app launch to `usage.json` next to the
service (capped to 60 entries). `getTiles` sorts by that stamp, newest first, then by the
priority list in `build_launcher.py`, then alphabetically.

## How it works

Two components run on the TV plus one build-time generator on your computer:

```
                    ┌───────────────────────── your computer ─────────────────────────┐
                    │  build_launcher.py   ── reads ──►  tiles.json + config.json    │
                    │        │  writes the boot-baked static HTML render             │
                    └────────┼───────────────────────────────────────────────────────┘
                             ▼
┌────────────────────────────────────────── webOS TV ──────────────────────────────────────┐
│  org.minimal.home  (web app)                        org.minimal.home.service  (Node)      │
│  ┌─────────────────────────┐                        ┌───────────────────────────────────┐  │
│  │ index.html + spatial-nav│  hello on boot ─────►  │ getTiles     live tile list + MRU │  │
│  │ static tiles → live     │  ◄───────────────      │ launchApp    intercept + record   │  │
│  │ build, re-sort on focus │                        │ openLGHome   bypass (10 min)      │  │
│  └───────────┬─────────────┘                        └───────────────┬───────────────────┘  │
│              │        foreground change (stock Home opened)        │                        │
│              │   ◄─────────────────────────────────────────────────┼────────────────────── │
│              │   watcher.js (event-driven, no polling) ────────────┘                        │
│              │        └─► re-launch org.minimal.home unless bypassed                        │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Build time** — `build_launcher.py` bakes a clean, static launcher from a launch-point
   snapshot so the screen renders instantly, before any service is reachable.
2. **Runtime app** — `index.html` calls `luna://org.minimal.home.service/getTiles`, rebuilds the
   grid from the live tile list, and re-sorts on every return to foreground.
3. **Relay service** — the app is a plain webOS *web* app, which cannot launch arbitrary apps
   directly; the service does the privileged `launch` calls for it and persists MRU data.
4. **Redirect watcher** — subscribes to `getForegroundAppInfo`. When stock `com.webos.app.home`
   comes to the foreground, it launches Minimal Home instead — unless the user just opened it via
   the "LG Home" tile, in which case the bypass file (`~/.noredirect`) is honored for 10 minutes.

## Repository layout

```
lg-root/
├── build_launcher.py        # build-time generator for the launcher page
├── launcher-app/            # the webOS web app (what runs on screen)
│   ├── appinfo.json         # webOS app manifest
│   ├── config.json          # header greeting config
│   ├── tiles.json           # sample launch-point snapshot for local builds
│   ├── spatial-nav.js       # shared D-pad / spatial navigation helper
│   └── index.html           # GENERATED by build_launcher.py (app entry point)
├── launcher-service/        # the Node relay service + redirect watcher
│   ├── service.js           # getTiles / launchApp / openLGHome + MRU persistence
│   ├── watcher.js           # event-driven LG Home → Minimal Home redirect
│   ├── services.json        # Luna service registration
│   └── package.json
└── private/                 # (git-ignored) personal dev tooling, backups, scripts
```

## Development

- **Build & iterate** — `python build_launcher.py` regenerates `index.html`.
  To preview in a desktop browser, comment out the `PalmServiceBridge`/`navigator.service`
  calls or open it with a small static server; the tile rendering and remote navigation work
  without Luna.
- **On-TV workflow** — the app can be pushed with any SFTP/SCP tool; the service needs
  `services.json` in place and a restart of the Luna service manager (`systemctl restart sam`
  on some firmware) to pick up the new service code.
- **Patches welcome** — see [CONTRIBUTING](CONTRIBUTING.md).

## Known limitations

- Requires a rooted TV — this is not a replacement for stock Home on unrooted firmware, and it
  does **not** bundle any root exploit.
- The MRU ordering persists only while the service dir is writable
  (`/media/developer/apps/usr/palm/services/org.minimal.home.service/`).
- Tested on **webOS 23**; older or newer firmware generations may differ in Luna API availability.
- The redirect watcher leans on `luna-send getForegroundAppInfo` subscribing; behavior may vary
  between firmware versions.

## Contributing

Issues, ideas and pull requests are welcome — from new themes and tile sections to input
management and accessibility. Start with [CONTRIBUTING](CONTRIBUTING.md). Please also review our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Disclaimer

**Use at your own risk.** This project modifies a rooted TV: you assume all responsibility for
your device, firmware, and warranty implications. Sensitive operational details
(credentials, personal snapshots, debug logs) intentionally live in the git-ignored `private/`
directory and are **not** part of the public repository. See [SECURITY](SECURITY.md).