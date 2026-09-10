# Releasing Minimal Home

Releases include a standard webOS IPK plus a source-built tar archive containing
the complete rooted-TV installer.

## Prepare

Complete the [contributor setup](../CONTRIBUTING.md#local-setup), including
`npm ci --ignore-scripts`, before running checks.

1. Update `version` in `launcher-app/config.json` using `MAJOR.MINOR.PATCH`.
2. Run `python build_launcher.py` and commit the source and generated outputs
   together. Do not use `--version` as a substitute for the source version.
3. Run `python tools/check.py`.
   Also complete the [full CI checklist](TESTING.md#full-ci-checklist), including
   Linux ShellCheck; the shared command is not the entire workflow.
4. Run `python tools/package.py --tag vVERSION`, replacing VERSION with the
   configured version. Inspect the IPK, source archive, and SHA-256 sidecars in
   `dist/`.
5. Record the TV models/firmware and device scenarios actually tested. Call out
   installation limitations and any unverified device behavior in release notes.
   Write these notes to `docs/releases/vVERSION.md` and commit them before tagging;
   the release workflow publishes that file as the release description.

Packaging rejects a mismatched tag or stale generated output. Both artifacts come
from an explicit allowlist in `tools/package.py`, excluding runtime state and
private files. Archive timestamps, ownership, ordering, and modes are normalized
so identical input bytes produce identical artifacts with the same Python/zlib
toolchain. Each SHA-256 sidecar records its artifact's digest.

## Publish

After review, create and push the corresponding `vVERSION` tag. The release
workflow first runs the shared CI workflow, then packages the checked source and
publishes the IPK, source archive, and checksums with the reviewed versioned
release notes.

The publish job has repository write permission; validation uses read-only
permissions. Workflow commands read the tag through an environment variable.
Actions are pinned to verified release commits; Dependabot checks for updates monthly.
Review the resulting release notes and include device-validation evidence.

Do not move a published tag to silently replace a release. Correct the source,
increment the version, and publish a new release. The project currently promises
no long-term support window; see the security policy in the repository root.
