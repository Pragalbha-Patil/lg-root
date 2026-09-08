# Releasing Minimal Home

Releases are source-built tar archives for an existing rooted installation, not
IPK packages or first-install automation.

## Prepare

Complete the [contributor setup](../CONTRIBUTING.md#local-setup), including
`npm ci --ignore-scripts`, before running checks.

1. Update `version` in `launcher-app/config.json` using `MAJOR.MINOR.PATCH`.
2. Run `python build_launcher.py` and commit the source and generated outputs
   together. Do not use `--version` as a substitute for the source version.
3. Run `python tools/check.py`.
4. Run `python tools/package.py --tag vVERSION`, replacing VERSION with the
   configured version. Inspect the archive and its SHA-256 sidecar in `dist/`.
5. Record the TV models/firmware and device scenarios actually tested. Call out
   installation limitations and any unverified device behavior in release notes.

Packaging rejects a mismatched tag or stale generated output. Files come from
an explicit allowlist in `tools/package.py`, excluding runtime state and private
files. Archive timestamps, ownership, ordering, and modes are normalized so
identical input bytes produce identical archives with the same Python/zlib
toolchain. The SHA-256 sidecar records the resulting archive digest.

## Publish

After review, create and push the corresponding `vVERSION` tag. The release
workflow first runs the shared CI workflow, then packages the checked source
and publishes the archive and checksum with generated release notes.

The publish job has repository write permission; validation uses read-only
permissions. Workflow commands read the tag through an environment variable.
Actions are pinned to verified release commits; Dependabot checks for updates monthly.
Review the resulting release notes and include device-validation evidence.

Do not move a published tag to silently replace a release. Correct the source,
increment the version, and publish a new release. The project currently promises
no long-term support window; see the security policy in the repository root.
