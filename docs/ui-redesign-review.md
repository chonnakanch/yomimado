# UI redesign verification and code review

Reviewed on 2026-10-15, starting from `0d2c1d0` on `develop`. This is source
verification after the owner's Phase 5 approval, without a version change or
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
eight-argument IPC commands. The return was removed. The two command boundaries
have narrow `expect(clippy::too_many_arguments)` annotations with explicit reasons
to retain their existing frontend contracts. These annotations check that the
expected lint still exists; they do not suppress other Clippy warnings. No command
arguments or coordinate behavior changed.

No additional confirmed correctness defects were found in the reviewed capture
session/cancellation, overlay publication/input routing, popup request invalidation,
Saved list/delete lifecycle, model setup, or OCR geometry-extension paths. This is
a focused review of the redesign and its integration boundaries, not a claim that
all application or platform behavior has been proven.

## Completed local checks

| Area | Result |
| --- | --- |
| Frontend | 172 tests in 20 files; TypeScript; normal and capture-debug production builds; full desktop Prettier check |
| Native macOS | 59 tests with all targets; locked debug build; Cargo formatting; strict Clippy for all targets with warnings denied |
| OCR service | 93 tests, zero failures/errors/skips; Ruff lint and formatting for app, tests and all packaged entrypoints/backend; dependency consistency check |
| Release tools | 229 unittest checks; Ruff lint and formatting across scripts |
| Patch | `git diff --check` |

Native checks used Rust 1.98.1. The complete service and release-tool suites used
the existing Python 3.11.17 environment, matching the project's CI interpreter.
The first service attempt used the older local `.venv` (Python 3.9): 92 tests
passed and the Windows graph verifier test failed because `hashlib.file_digest`
is a Python 3.11 API. Rerunning the entire suite with 3.11.17 passed all 93 tests;
no compatibility shim, skipped test, model download or dependency change was used.
OCR tests ran with Hugging Face and Transformers offline flags enabled.

## Remaining acceptance boundaries

- Local compilation/tests cover macOS. Windows compilation is delegated to the
  existing Checks workflow; interactive Windows/mixed-DPI acceptance remains open.
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

The review left the running development app, OCR service and user-local design
references in place. No new phase or unrelated refactor was started.
