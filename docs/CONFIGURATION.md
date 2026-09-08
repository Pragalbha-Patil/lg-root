# Configuration

## Source configuration

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

## On-TV configuration

The runtime file is
`/media/developer/apps/usr/palm/services/org.minimal.home.service/config.json`.
The relay rereads it for every `getTiles` request, including startup, return to
foreground, and relaunch. The frontend applies the greeting, system-row IDs,
and Settings action from that response; app priority sorting happens in the relay.
This works on the next TV boot without rebuilding. Editing the app directory's
copy has no runtime effect.

Follow the [README commands](../README.md#change-configuration-on-the-tv) to edit
and refresh while the TV is running. A direct `getTiles` call can inspect the
configuration response but does not itself refresh the visible page. No continuous
config polling is performed.

Use strings for both header fields and arrays of app ID strings for both `ui`
fields. Retain all fields when editing: runtime reads do not merge build defaults.
An empty `ui.system` hides system apps, including the Settings tile, while the
header gear and LG Home bypass remain available. IDs only expose apps returned
by live discovery. `ui.appsPriority` breaks ordering ties after pins and recent
usage; alphabetical sorting ignores it.

`version` remains build metadata: changing it on the TV does not update the
installed manifest or displayed build version. Appearance and clock options
belong to launcher preferences below.

The initial feature installation needs updated app and relay files and a restart
of their existing processes; subsequent config edits do not. Uploading a build
or release overwrites the service config, so keep a backup of TV customizations
and reapply them afterward. Invalid JSON or invalid field types can leave the
greeting blank or system apps hidden; restore the backup and refresh if needed.

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
