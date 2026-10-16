# UI redesign verification and code review

Reviewed on 2026-10-15, starting from `0d2c1d0` on `develop`, with the owner's
subsequent request to remove lint exceptions and prepare Windows coverage. This is
source verification after the owner's Phase 5 approval, without a version change or
installer publication.

## Review findings

### Fixed: More actions could hide a destination failure

The popover dismisses itself before opening Saved, Settings, Sources or keyboard
reading. If the subsequent native command failed, its catch handler rendered the
error inside the hidden popover. The user received no visible failure indication.

The menu now sends failures to the toolbar through a targeted Tauri event. The
existing status icon and accessible alert retain the error, and the status details
show its message on request. Menu placement, focus behavior and successful actions
are unchanged. Two regression tests cover the failure handoff and its presentation
after dismissal. The menu-side test failed against the previous implementation.
Existing core event permissions already permit this handoff.

### Resolved: strict native lint findings

Clippy found one unnecessary return in macOS pointer-display selection and two
eight-argument IPC commands. The return was removed. The initial review used two
narrow argument-count expectations; the owner then requested a refactor, and both
expectations are now removed. Overlay controls obtain the app handle from their
injected window. The translation popup obtains demo/manga mode from the stored
native OCR result instead of a redundant frontend flag. Each command has seven
parameters, and coordinate and focus behavior remain unchanged.

The native CI matrix now installs Clippy and runs it for all targets with warnings
denied on both macOS and Windows. A shared native regression test exercises all
16 scale transitions among 100%, 125%, 150% and 200%, plus shifted/clipped frames
at negative origins. The existing stale-frame guard is unchanged in behavior and
is now directly tested; a DPI change invalidates old hits even with unchanged
physical window dimensions.

The first strict Windows run also exposed dead code: macOS pointer-sampling
fields/helpers and bundled-service startup plumbing were compiled into Windows
development targets that cannot use them. These now have explicit platform/build
conditions, without warning suppression. Release service startup/cleanup retain
their existing code and configuration. The Windows service module still compiles
under tests, preserving its real SDK-layout, job-termination and readiness tests.

At the initial review, no additional confirmed correctness defects were found in the reviewed capture
session/cancellation, overlay publication/input routing, popup request invalidation,
Saved list/delete lifecycle, model setup, or OCR geometry-extension paths. This is
a focused review of the redesign and its integration boundaries, not a claim that
all application or platform behavior has been proven.

### Fixed: concurrent OCR requests shared model state

A follow-up review confirmed that overlapping requests could initialize two model
pairs or enter the same detector concurrently. Canceling a desktop request does
not guarantee its inference worker has stopped. The service now admits one
recognition worker at a time, including model initialization, and rejects overlap
with HTTP 503 and `Retry-After: 1`. The lock belongs to the worker and is released
only after recognition finishes or fails; there is no waiting screenshot queue.
Four regression cases cover overlap, cancellation, and recovery after both input
and model errors. The overlap and cancellation cases failed before the fix.

### Fixed: Windows installed smokes targeted the previous UI

The release UI smoke now discovers the toolbar, More actions and Settings windows
by owned process and title. It uses Selected Area / Whole Screen and the selector's
edge hint. Model import remains scoped to Settings, and native Settings close must
leave the toolbar alive. Both installed smoke scripts now invoke More actions →
Quit YomiMado before checking exit, instead of treating native close as Quit.
Bundled-service identity, child cleanup, port release and model-hash checks remain.

A shared Windows PowerShell 5.1 driver supports button and menu-item automation.
Checks CI runs it against two synthetic WPF processes with identical window
titles, verifying PID isolation, a taskbar-skipping toolbar, Settings close/reopen,
and explicit Quit. This validates the driver without building an installer; it
does not establish installed Tauri UI or physical mixed-DPI acceptance.

## Completed local checks

| Area          | Result                                                                                                                                           |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Frontend      | 172 tests in 20 files; TypeScript; normal and capture-debug production builds; full desktop Prettier check                                       |
| Native macOS  | 60 tests with all targets; locked debug build; Cargo formatting; strict Clippy for all targets with warnings denied                              |
| OCR service   | 97 tests, zero failures/errors/skips; Ruff lint and formatting for app, tests and all packaged entrypoints/backend; dependency consistency check |
| Release tools | 229 unittest checks; Ruff lint and formatting across scripts                                                                                     |
| Patch         | `git diff --check`                                                                                                                               |

Native checks used Rust 1.98.1. The complete service and release-tool suites used
the existing Python 3.11.17 environment, matching the project's CI interpreter.
The first service attempt used the older local `.venv` (Python 3.9): 92 tests
passed and the Windows graph verifier test failed because `hashlib.file_digest`
is a Python 3.11 API. Rerunning the entire suite with 3.11.17 passed all 93 tests;
no compatibility shim, skipped test, model download or dependency change was used.
OCR tests ran with Hugging Face and Transformers offline flags enabled.
The follow-up reran all 97 service tests and 229 release-tool tests, service/script
lint and formatting, and workflow formatting. On 2026-10-16,
[Checks run 38836706682](https://github.com/chonnakanch/yomimado/actions/runs/38836706682)
passed for `e0ebe97`: frontend, service, release tools, strict Clippy, native tests
and debug builds on macOS/Windows, and the synthetic Windows UI driver test.
The aggregate gate also passed. No release workflow was dispatched.

## Remaining acceptance boundaries

- Local compilation/tests cover macOS. The initial review's
  [Checks run 38744718738](https://github.com/chonnakanch/yomimado/actions/runs/38744718738)
  passed frontend, service, release tools and macOS/Windows native tests/builds
  for `0fbb89d`. The follow-up adds strict Clippy to both native CI jobs.
  The owner chose automated coverage and a
  [Windows checklist](ui-redesign-windows-checklist.md) for later interactive
  Windows/mixed-DPI verification; those manual results remain unrecorded.
- The new error handoff has automated component coverage and verified permissions,
  but no deliberate native window-creation failure was injected into the owner's
  running reading session.
- Automated service tests exercise API, geometry, security, dictionaries and
  persistence with test inputs. They do not repeat the owner's live manga-model
  inference or certify recognition accuracy on arbitrary manga.
- Native close/reopen, simultaneous secondary windows, multi-monitor/Spaces and
  Quit/service-cleanup acceptance retain the separate checklist in
  [the implementation plan](implementation-plan.md). Vorssaint's external
  quit-on-close behavior and the owner's exception choice are unchanged.
- No installer, frozen OCR runtime or release artifact was rebuilt or approved.
  The OCR service source changed in the follow-up. A future macOS frozen-runtime
  seed must be refreshed and reviewed before packaging; the existing source/seed
  mismatch rejection is preserved.

The review left the running development app, OCR service and user-local design
references in place. No new phase or unrelated refactor was started.
