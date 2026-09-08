# Configuration

## Build configuration

Edit `launcher-app/config.json`, then run `python build_launcher.py` and deploy
both app and service files. The generated service-local copy is necessary
because the service cannot reliably read the app directory.

| Field | Meaning |
| --- | --- |
| `version` | Three-part app version, such as `1.3.2` |
| `header.text` | Small greeting text |
| `header.brand` | Emphasized greeting text |
| `ui.system` | System apps exposed as tiles; includes optional TV Settings |
| `ui.appsPriority` | App IDs used to break ties after recent usage |

Example greeting:

```json
{
  "header": {
    "text": "Welcome",
    "brand": "Minimal Home"
  }
}
```

Missing fields inherit defaults. Invalid JSON, wrong field types, and invalid
version strings fail the build. The committed startup banner remains generic;
the live relay supplies the configured greeting.

Inputs are discovered from the TV's launch points. Do not add a fixed HDMI list
to config. The system allowlist is explicit: an empty list hides all system
apps, including the Settings tile. The header gear still opens launcher preferences,
and the LG Home bypass tile remains available.

## Launcher preferences

Open the Settings tile or header gear. Left/Right cycles options; OK activates a
row; Back closes the panel.

Preferences include accent color, tile size, labels, clock options, date format,
sort mode, and system statistics. Use the per-tile menu to pin/unpin or hide an app;
restore hidden apps from Settings. Reset all restores defaults.

Preferences live in `prefs.json` next to the service on the TV, not in the build
config. The installer preserves these files. Recently used sorts by launch recency,
with pinned apps first and configured priority as a fallback. Pinned first ignores
recency and uses configured priority/title after pins. Alphabetical ignores pin
ordering. Pin badges remain visible in every mode.

## Desktop preview tiles and personal usage

`launcher-app/tiles.json` is a public sample snapshot used only with `--preview`.
Normal builds start with a loading indicator and populate the rows from the TV.
System app IDs in the config filter live results; they do not create tiles.
Missing desktop icons are expected because the watcher provisions app-local icons on the device.

Default builds use only public inputs. To bake a personal recent-app ordering:

```sh
python build_launcher.py --preview --usage private/usage.json
```

Supply a JSON object mapping app IDs to nonnegative integer launch sequence
values. There is no automatic lookup of `usage.json` in app or service directories.

Sample and personal output are for local desktop preview.
The installer and release packager require the default reproducible build and
will reject a personalized page that differs. Before opening a PR, restore it:

```sh
python build_launcher.py
python tools/check.py
```

Keep personal snapshots and credentials in the ignored `private/` directory.
