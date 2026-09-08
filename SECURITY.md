# Security Policy

## Supported versions

This project has no long-term-support window and no released version numbers to
speak of yet — we support the latest state of the `master` branch. Fixes land
there first.

## Reporting a vulnerability

Please **do not open a public issue** for security vulnerabilities. Instead,
report them privately to the repository owner (contact address on their GitHub
profile) and give us a reasonable time window (a couple of weeks) to respond
before disclosing publicly.

When reporting, please include:

- The affected component (`launcher-app`, `launcher-service`, `build_launcher.py`)
- TV model and webOS version
- Steps to reproduce
- Impact (what a malicious actor could do) and any proposed fix

## Scope and stance

This project is a **root-level** tool for rooted LG webOS TVs. By design it runs
as `root` on the target device. Threats we care about:

| Concern                                                | Our stance                                                                  |
| ------------------------------------------------------ | --------------------------------------------------------------------------- |
| The tool helping unauthorized root access               | Out of scope — the tool assumes you already rooted your own TV.              |
| Credentials / TV addresses leaking into the repo        | **Critical.** This repo was previously a working directory containing real   |
|                                                        | credentials and session logs. They now live in the git-ignored `private/`    |
|                                                        | directory. A regression here is a bug — see below.                           |
| Luna service exposing privileged actions to other apps | Should be reviewed on change. The service intentionally performs privileged  |
|                                                        | launches; it does not expose arbitrary shell execution.                      |
| Supply chain (malicious deps)                          | The runtime has effectively no third-party dependencies (Node built-ins).   |

### The `private/` rule

`private/` is personal working state (device addresses, SSH credentials, command
history, backups, session logs). It must remain git-ignored. If you ever see
anything from `private/` staged or committed — or a *.txt / *.md with real
credentials — that is a security regression: remove the secret, rotate the
credential if it was published, and report it.

## Deployment hygiene for maintainers

- Never commit `tv-ops-log.txt`, `lg-webos-*.md` session logs, or backup trees.
- Before any commit, run `git status` and confirm `private/` shows nothing staged.
- Consider rotating the TV's SSH password before and after making this repository
  public, since the historical commit history predates the cleanup.