# Security policy

## Supported versions

Security fixes target the latest code on `main`. There is no long-term support
window or commitment to backport fixes to older releases.

## Report a vulnerability

Do not post exploit details or credentials in a public issue. Use
[GitHub private vulnerability reporting](https://github.com/Pragalbha-Patil/webos-minimal-home/security/advisories/new)
if available for this repository. Otherwise contact the repository owner through
the contact information on their
[GitHub profile](https://github.com/Pragalbha-Patil).

Include the affected commit/version and component, TV model and webOS version,
reproduction steps, expected impact, and a suggested fix if you have one.
Redact device addresses, credentials, tokens, and identifying logs. Coordinate
disclosure with the maintainer; no fixed response-time commitment is made.

## Security boundary

Minimal Home assumes an already rooted TV controlled by its owner. The root
watcher runs with elevated access; the relay relies on Luna permissions. It
does not provide a root exploit.

Review changes that affect Luna authorization, launch parameter validation,
remote commands, file paths, or uploaded files carefully. The relay depends on
the platform-provided `webos-service` module in addition to Node built-ins;
Python build/package tooling uses the standard library. Host JavaScript checks
use development packages pinned by `package-lock.json`; they are excluded from
TV release payloads. Install them with `npm ci --ignore-scripts`.

The installer stages an explicit runtime allowlist and preserves TV state.
CI checks known private/runtime paths and generated output, but it is not a
complete secret scanner or an audit of historical commits.

## Private data

Keep credentials, real TV addresses, backups, usage snapshots, and session
history in the ignored `private/` directory or outside the repository.
Runtime `usage.json`, `prefs.json`, bypass files, logs, and provisioned icons
must not be committed or included in public packages.

Before submitting a change, inspect `git diff` and `git status --short`.
If a credential was exposed, revoke or rotate it; deleting it in a later commit
does not remove it from repository history. Report the exposure privately.
