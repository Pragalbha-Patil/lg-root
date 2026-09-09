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

## Upload from a source checkout

Build on your computer with Python 3.10+. Use a POSIX shell with SSH/SCP installed;
on Windows use Git Bash or WSL. Configure an SSH host alias such as `mytv`.

```sh
TV_HOST=mytv sh tools/install.sh --check
TV_HOST=mytv sh tools/install.sh
```

The directory check is read-only and does not prove Luna registration works.
Normal upload creates missing target directories, builds, checks generated-file
freshness, stages the runtime file allowlist, preserves the installed configuration,
uploads it, and requests launch.
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
files. If a service-local `config.json` exists, the helper reads and validates it
before uploading anything, then merges its custom values onto the new schema.
New fields and the release version are retained automatically. A malformed existing
config stops the update before TV files change. The helper does not terminate
existing processes or replace boot hooks.

## Upload a release archive

On your computer, extract `minimal-home-vVERSION.tar.gz` into an empty directory.
The archive contains only runtime files, the installer, this guide, and the
license. If a checksum file was downloaded alongside the archive, verify it
before extraction:

```sh
sha256sum -c minimal-home-vVERSION.tar.gz.sha256
tar -xzf minimal-home-vVERSION.tar.gz
```

In the extracted directory, replace `mytv` with your SSH alias and run the bundled
installer. It provides the same automatic configuration preservation as a source
checkout:

```sh
TV_HOST=mytv sh tools/install.sh
```

The archive contains only allowlisted files, not personal runtime state. It is not
an IPK and does not register services.

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

Use the LG Home tile after successful discovery. If the grid never loads or the
UI is unusable, but the relay is registered and can launch Home, this
**state-changing command on the TV** requests the same temporary bypass:

```sh
luna-send -n 1 luna://org.minimal.home.service/openLGHome '{}'
```

Require `returnValue: true`. A failed Home launch removes the bypass marker and
reports an error. If the relay is missing or denied, do not widen permissions;
use the targeted watcher/boot-hook recovery below.

The bypass stores a wall-clock expiry for ten minutes. It suppresses redirects,
not a timer that forcibly switches the screen at expiry. A later relevant
foreground event can resume redirection. Restarting only the webview does not
cancel the persisted bypass. Stopping the watcher suppresses redirects until
it is started again; disabling its boot hook also prevents startup on reboot.

For a lasting rollback, disable
the watcher boot hook you installed and stop its specific process, then launch
stock Home:

```sh
luna-send -n 1 luna://com.webos.applicationManager/launch '{"id":"com.webos.app.home"}'
```

Once stock Home works, remove Minimal Home app/service registrations using the
same mechanism that created them. Keep a backup of preferences if needed before
removing the app/service directories. Do not delete unrelated LS2 registrations.
