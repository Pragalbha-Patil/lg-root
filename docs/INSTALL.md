# Installation and recovery

Minimal Home requires an already rooted LG webOS TV with SSH access. It does not
include a root exploit. The [webOS Homebrew project](https://www.webosbrew.org)
provides information about rooting and the Homebrew environment.

## First-install boundary

Copying these files alone is **not a complete first-install process**. The web app
and relay must be registered with Luna, and the relay needs permissions to query
and launch applications. This repository does not yet automate that firmware-
dependent setup or install a persistent watcher boot hook.

Before using the upload helper, establish app/service registration through your
root environment. Existing project observations use dev-mode LS2 registration
under `/var/luna-service2-dev/` and client permissions under
`/var/luna-service2/`. The app client uses the `public` group; the relay needs
`public`, `applications`, `applications.launch`, `applications.query`, and
`applications.internal`. Registration details vary by firmware; do not assume
`services.json` alone grants these permissions.

On the TV, check the relay:

```sh
luna-send -n 1 luna://org.minimal.home.service/getTiles '{}'
```

Proceed when it returns `returnValue: true`. A missing-service or denied-method
response is a registration/permissions problem, not a reason to broaden all app
permissions.

## Before upgrading

Both upload paths overwrite shipped files, including **service-local config.json**.
They preserve unshipped `prefs.json`, `usage.json` and the icon cache, but this is
not a backup of your custom greeting, system allowlist or app priorities.

1. Keep a working SSH session and your current known-good release archive. Record
   how your installation starts the watcher and registers the relay.
2. Download a backup of the service-local `config.json` into a private directory
   on your computer before upload. Also back up `prefs.json` and `usage.json` if
   present and important. Do not publish these files or put them in release payloads.
   For example, from an already created private backup directory:

   ```sh
   scp root@mytv:/media/developer/apps/usr/palm/services/org.minimal.home.service/config.json config-before-upgrade.json
   ```

3. After upload, compare the saved config with the new service config. Reapply
   intended customizations to the new schema, preserving new fields and build
   metadata; do not blindly overwrite it with the old file. Validate JSON, replace
   it atomically, and refresh the launcher. The source README describes this flow.
4. Restart only your launcher webview, relay and watcher through the existing
   device workflow. Verify the scenarios in **Updating and verifying**.

If a copy is interrupted, do not launch the partially updated installation.
Re-upload a complete verified release. To roll back, stop the specific watcher
and disable its boot hook, confirm stock Home works, then upload the previous
known-good release and merge its compatible config from your backup. Restart the
specific processes and verify before re-enabling the hook. No broad platform
restart or removal of unrelated registrations is required. Recovery commands
depend on the registration/boot mechanism you originally installed.

## Upload from a source checkout

Complete **Before upgrading** above before uploading to an existing installation.

Build on your computer with Python 3.10+. Use a POSIX shell with SSH/SCP installed;
on Windows use Git Bash or WSL. Configure an SSH host alias such as `mytv`.

```sh
TV_HOST=mytv sh tools/install.sh --check
TV_HOST=mytv sh tools/install.sh
```

The directory check is read-only and does not prove Luna registration works.
Normal upload creates missing target directories, builds, checks generated-file
freshness, stages the runtime file allowlist, uploads it, and requests launch.
SSH/SCP failures and unsuccessful Luna launch replies produce a nonzero exit.

| Variable/option | Purpose |
| --- | --- |
| `TV_HOST` | Required SSH alias, hostname, or IPv4 address; use an alias for IPv6 |
| `TV_USER` | SSH user, default `root` |
| `PYTHON` | Python executable, default `python`; set `python3` if needed |
| `--check` | Check remote app/service directories without modifying them |
| `--no-build` | Skip generation; still require up-to-date generated files |

App and service IDs are fixed in manifests and code. Environment overrides to
different IDs are rejected. The helper can run from any current directory.
It preserves TV preferences, usage history, and icons by uploading only shipped
files. It does not terminate existing processes or replace boot hooks.

## Upload a release archive

Complete **Before upgrading** above first.

On your computer, extract `minimal-home-vVERSION.tar.gz` into an empty directory.
The archive contains only runtime files, this guide, and the license. If a
checksum file was downloaded alongside the archive, verify it before extraction:

```sh
sha256sum -c minimal-home-vVERSION.tar.gz.sha256
tar -xzf minimal-home-vVERSION.tar.gz
```

In the extracted directory, replace `mytv` with your SSH alias and upload:

```sh
ssh root@mytv "mkdir -p /media/developer/apps/usr/palm/applications/org.minimal.home /media/developer/apps/usr/palm/services/org.minimal.home.service"
scp -r launcher-app/. root@mytv:/media/developer/apps/usr/palm/applications/org.minimal.home/
scp -r launcher-service/. root@mytv:/media/developer/apps/usr/palm/services/org.minimal.home.service/
ssh root@mytv "luna-send -n 1 luna://com.webos.applicationManager/launch '{\"id\":\"org.minimal.home\"}'"
```

Use recursive copies only from the extracted release, whose contents exclude
personal runtime files. An archive is not an IPK and does not register services.

## Start the watcher

The watcher runs separately from the on-demand relay. On the TV, after confirming
that another watcher instance is not already running:

```sh
setsid node /media/developer/apps/usr/palm/services/org.minimal.home.service/watcher.js \
  </dev/null >/dev/null 2>&1 &
```

For persistence, integrate that command into your root environment's boot hook
after Luna is available. webOS Homebrew setups commonly use executable scripts
under `/var/lib/webosbrew/init.d/`. Keep hooks LF-only and validate them with
`sh -n` before enabling them. Hook installation is currently manual.

## Updating and verifying

Uploading files may leave the previous code in running processes. Close and
relaunch the webview; restart the specific relay and watcher processes through
your existing device workflow. The on-demand relay loads new code on its next
start. Broad platform restarts can interrupt other apps and are not performed
by the installer.

Verify app launch, return from another app, D-pad/OK/Back, preferences after
relaunch, input switching, and the ten-minute LG Home bypass. Confirm the
watcher is running only once. Icon provisioning first runs shortly after watcher
startup and repeats every five minutes.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Relay missing or Luna denied | App/service registration and client permissions |
| Uploaded UI looks unchanged | Running webview may still contain old code |
| Header/config missing | Deploy both app and generated service config |
| Blank/missing icons | Root watcher running; icons copied into the app's directory |
| Home button still opens LG Home | Watcher subscription and bypass expiry |
| Input opens to a black screen | Live launch-point parameters and input regression tests |
| System stats unavailable | Watcher running, stats enabled, and readable device counters |

Service logs are at `/tmp/minhome-svc.log`; watcher logs are at
`/tmp/minhome-watch.log`. They disappear on reboot. Redact identifying information
before sharing logs. A browser-only preview cannot validate these platform behaviors.

## Return to stock Home

Use the LG Home tile for a ten-minute bypass. For a lasting rollback, disable
the watcher boot hook you installed and stop its specific process, then launch
stock Home:

```sh
luna-send -n 1 luna://com.webos.applicationManager/launch '{"id":"com.webos.app.home"}'
```

Once stock Home works, remove Minimal Home app/service registrations using the
same mechanism that created them. Keep a backup of preferences if needed before
removing the app/service directories. Do not delete unrelated LS2 registrations.
