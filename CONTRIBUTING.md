# Contributing to Minimal Home

First off — thank you for considering a contribution. This project started as a personal
launcher on a rooted LG webOS TV, and the goal of making it public is to let the community
grow it into something better.

All contributors are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Table of contents

- [Ground rules](#ground-rules)
- [Getting started](#getting-started)
- [How to contribute](#how-to-contribute)
  - [Report a bug](#report-a-bug)
  - [Propose a feature](#propose-a-feature)
  - [Write code](#write-code)
- [Development environment](#development-environment)
- [Where things live](#where-things-live)
- [Good first issues](#good-first-issues)

## Ground rules

1. **No secrets in the public tree.** This repository once contained private working state
   (TV addresses, SSH credentials, session logs). That tooling now lives in the git-ignored
   `private/` directory and must **never** be committed. Double-check `git status` before
   committing: nothing under `private/` should ever be staged.
2. **Respect that most users have a rooted TV but not your TV.** Avoid hardcoding IPs,
   credentials, or hardware specifics in contributions. Add config or environment-variable
   hooks instead.
3. **A rooted TV is the user's responsibility.** Document risks; never downplay them.
4. Keep changes focused. One pull request = one logical change.

## Getting started

1. Fork the repository.
2. Clone your fork:
   ```sh
   git clone https://github.com/<your-user>/webos-minimal-home.git
   cd webos-minimal-home
   ```
3. Create a branch:
   ```sh
   git checkout -b feature/your-change
   ```
4. Make your changes (see [Development environment](#development-environment)).
5. Build to confirm nothing is broken:
   ```sh
   python build_launcher.py
   ```
6. Commit with a clear message, e.g. `launcher-service: skip fullscreen apps in getTiles`.
7. Push and open a pull request describing **what** you changed and **why**, plus how you tested it.

## How to contribute

### Report a bug

Open an issue and include:

- TV model and webOS version (Settings → Support → Software info / `systemctl` version output)
- How you installed Minimal Home (boot hook, manual scp, etc.)
- Steps to reproduce
- What you expected to happen vs. what happened
- Relevant logs (`/tmp/minhome-svc.log`, `/tmp/minhome-watch.log`)

### Propose a feature

Open an issue describing the feature, the problem it solves, and rough idea of the approach.
Small, well-scoped proposals are much easier to accept than large rewrites.

### Write code

- **Follow existing patterns.** The codebase is deliberately small and dependency-light:
  plain ES5 where possible (older webOS builds lack newer JS features), no build toolchain beyond
  Python, vanilla CSS/JS.
- **Comment only where the *why* matters**, not the what.
- **Verify on device if you can.** Not every fix can be tested in a browser; but if you can at
  least confirm the build runs (`python build_launcher.py`) and, where applicable, that the
  generated page renders, that goes a long way.

## Development environment

- Python 3.7+ (build script only).
- Optionally `node` locally, but the service runs **on the TV**, so most service changes need
  an actual device to validate.
- No third-party runtime dependencies for the launcher itself.

## Where things live

| Area                          | Location                  | Notes                                              |
| ----------------------------- | ------------------------- | -------------------------------------------------- |
| Launcher page (UI + build)    | `launcher-app/`, `build_launcher.py` | `index.html` is generated — edit the generator, not the artifact |
| Relay service (Luna API)      | `launcher-service/service.js`       | `getTiles`, `launchApp`, `openLGHome`, MRU storage |
| LG Home redirect watcher      | `launcher-service/watcher.js`       | Event-driven foreground watcher                    |
| Personal dev tooling + backups| `private/` (ignored)     | Never committed                                    |

## Good first issues

Look for issues labelled `good first issue`. Ideas the community has already flagged:

- Additional tile sections (e.g. a configurable "pinned" row)
- Theme / accent color configuration
- Input power / CEC integration on tile focus
- Better first-run experience / onboarding instructions
- Accessibility improvements for remote-driven focus