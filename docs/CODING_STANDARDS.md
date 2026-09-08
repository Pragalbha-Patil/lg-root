# Coding standards

Minimal Home favors a small dependency surface, explicit platform boundaries,
and changes that can be tested without a TV.

## General

- Match nearby code; keep formatting-only changes separate from behavior changes.
- Use names that describe the value or action. Comment on platform constraints
  and intent, especially where an apparently simpler implementation breaks webOS.
- Keep parsing, validation, and side effects separate where practical.
- Validate values at file, process, and Luna boundaries. Do not silently turn a
  malformed required config into defaults.
- Prefer a small helper when it removes meaningful duplication. Avoid adding a
  framework for a single use case.
- Use UTF-8, LF line endings, and a final newline. Editor defaults live in
  `.editorconfig`; shell LF behavior is enforced by `.gitattributes` and checks.

## Python host tools

Use Python 3.10+ and the standard library. Use four-space indentation and
`snake_case`. Make imports safe: commands belong in `main()` behind a
`__name__ == "__main__"` guard.

Specify UTF-8 when reading or writing text and LF when writing generated files.
Builds and packages should depend on declared input files, not local runtime
state or timestamps. Report invalid user input with a useful error and nonzero exit.

Use argument lists for subprocesses, `check=True` when failures matter, and
timeouts for potentially hanging checks. Avoid `shell=True` for data arguments.
Use temporary directories for isolated tooling tests and patches/context managers
to restore modified globals.

## JavaScript on the TV

The frontend embedded in `build_launcher.py` and the relay in `service.js`
use ES5 syntax: `var`, functions, and callbacks. The relay uses four-space
indentation and single quotes; keep the embedded template's existing conventions.

The root watcher already uses `const`, promises, async functions, and Node
filesystem APIs. A syntax check on host Node does not prove these APIs work on
every TV. Verify new runtime APIs against the intended device before relying on
them. Do not introduce npm-installed runtime dependencies.

At Luna boundaries, respond with `returnValue` and useful `errorText` on failure.
Handle asynchronous errors inside the callback as well as errors starting the
request. Do not swallow failures that determine whether a requested operation
succeeded. Logging or optional telemetry failure may be best-effort.

Keep log growth and retry loops bounded. Clear timers when their work is no
longer needed, coalesce duplicate events, and avoid rewriting identical files to
TV storage. Preserve input parameter filtering, the Home bypass, and refresh on
return to foreground.

## HTML and CSS

Edit the generator, then rebuild. Escape text and attribute values at the output
boundary; do not concatenate untrusted launch-point content into markup.
Keep focus visible and all interactive controls usable with D-pad, OK, and Back.
A visual change should account for TV viewing distance and missing icons.

## Shell and deployment

Use POSIX sh, `set -eu`, quoted expansions, and explicit argument validation.
Keep SSH destinations separate from remote command data. A failed upload or
launch must produce a nonzero exit. Do not interpolate arbitrary values into
remote shell code.

Stage deployment files through the allowlist in `tools/package.py`; never copy a
developer's entire working directory or runtime preferences to another device.
Do not make disruptive platform restarts an implicit part of file upload.

## Tests and documentation

Use `unittest` and the existing Node VM harness pattern with mocked Luna,
filesystem, timers, and child processes. Assert the behavior that would regress,
rather than only the presence of a string in source. Keep bug fixtures small and
synthetic. Give subprocess harnesses a timeout when adding or changing them.

Update the relevant guide when changing a command, config field, deployment
contract, or runtime boundary. Link to a shared explanation instead of copying it
into the README, contributor guide, and agent guide. Avoid fixed test counts,
unverified compatibility claims, and commands depending on private scripts.
