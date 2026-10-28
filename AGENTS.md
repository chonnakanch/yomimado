# YomiMado — contributor-agent instructions

Read `@/Users/chonnakan/.codex/RTK.md` for local command conventions.

## Project and current scope

YomiMado is an open-source Japanese manga reading assistant for macOS
and Windows. **Capture → recognize → click → learn** preserves the original
manga and adds interactive learning information. The name has not been
trademark/domain/package cleared.

Use the [implementation plan](docs/implementation-plan.md) for current feature
status and maintenance priorities, and the [release checklist](docs/desktop-release.md)
for recorded releases, source identities and exact-installer evidence.

Start with [docs/README.md](docs/README.md). Read the relevant canonical guide:

| Work                                                       | Guide                                                                                    |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Current status, proposed features and completion criteria  | [Implementation status and roadmap](docs/implementation-plan.md)                         |
| Source tree, API contracts, coordinates and resource roles | [Architecture and resources](docs/architecture.md)                                       |
| Local setup, models, checks and diagnostics                | [Development](docs/development.md)                                                       |
| Packaged-app installation and first-run setup              | [Installation guide](docs/installation-guide.md)                                         |
| Reading controls and saved collections                     | [Usage](docs/usage.md)                                                                   |
| UI tokens, component behavior, tray and icons              | [Design system](docs/design-system.md)                                                   |
| Native overlay, Windows/DPI and UI review evidence         | [UI testing](docs/ui-testing.md)                                                         |
| Branches, commits, PRs and merges                          | [Git conventions](docs/git-conventions.md)                                               |
| Versions, macOS seeds and publication gates                | [Release runbook](docs/release-runbook.md), [desktop checklist](docs/desktop-release.md) |

Implement only the requested scope. Prioritize release readiness and maintenance
unless the owner requests a feature. Previously proposed features do not authorize
implementation. The UI redesign is already implemented; do not restart it from
historical plans. Bubble retry/redraw was removed at the owner's request. Anki
export is excluded from the current roadmap. Do not request more v0.1.0 testing.

## Product and implementation rules

- Keep OCR and dictionary lookup local. Never upload screenshots automatically.
  Translate and save only on request; preserve original Japanese and cache repeated
  translations by provider identity and source text. Send minimum necessary context.
- Preserve the original manga. Use transparent, always-on-top OCR overlays and
  anchored learning popups; avoid opaque page coverage or translated-image output.
- Treat vertical Japanese, OCR geometry and physical/logical display scaling as
  first-class data. Preserve polygons, orientation, confidence, text type and review
  metadata through the API; never reduce OCR results to strings alone.
- Keep the single tested coordinate path explicit: screen physical pixels →
  captured image pixels → OCR image coordinates → overlay logical coordinates →
  mouse/event coordinates. Account for Retina, Windows fractional scaling and
  negative monitor origins; do not scatter scale calculations or magic constants.
- Expose uncertainty rather than silently guessing. Recognition confidence `0`
  means unknown. Keep sound-effect handling distinct from dialogue where appropriate.
- Keep frontend contracts independent of Python internals and providers behind
  small interfaces. Preserve source-text Unicode code-point offsets, readings,
  dictionary forms and parts of speech during analysis.
- Prefer simple, strongly typed, feature-focused code and a small vertical slice.
  Handle errors explicitly at process/API boundaries. Log useful capture/OCR
  diagnostics without screenshot contents or recognized text by default.

The desktop uses Tauri 2, React/TypeScript and Rust. Use Tauri global shortcuts
and the isolated xcap capture abstraction; identify platform requirements before
changing capture/overlay code. macOS Apple Silicon and Windows 11 x64 are release
targets. Do not add Linux/mobile support without an explicit request.

The local Python service separates comic-text-detector geometry from Manga OCR
recognition. Learning analysis uses **Lindera 6.0.0 and hash-pinned IPADIC** behind
its application interface; Sudachi remains comparison-only. JMdict supplies word
meanings and KANJIDIC2 supplies kanji details; they do not replace morphology.
SQLite holds derived dictionary indexes, translation cache and saved learning data.
Current translation choices are imported local Marian or local Ollama, selected
explicitly. Provider implementations belong outside OCR/tokenization logic.
See architecture for platform inference differences and current API/type files.

Maintain word readings, meanings, dictionary forms and POS; sentence Japanese with
explicit translation; kanji readings, meanings and example compounds. Capture stays
an explicit shortcut/selection/page-scan flow. The opt-in Auto detect mode watches
only an explicitly scanned fixed area. Other continuous OCR, browser extensions,
full panel reading-order reconstruction, image replacement/inpainting, cloud OCR,
accounts, cloud sync, advanced Anki and pitch-accent data require new scope.

## Licensing and release evidence

Before adding or bundling a dependency, verify the exact version's software,
model and data terms separately. Pin versions and dictionary hashes. Maintain
`THIRD_PARTY_LICENSES/`, required attribution, full licences, provenance and
corresponding sources. Repository code, weights, fonts and datasets need separate
review. Respect the applicable terms when using reference code; prefer direct
components or a clean implementation over copying entire reference apps.

Do not commit copyrighted manga screenshots. Use synthetic/public-domain assets
or private local fixtures. Do not commit models, local databases or build staging.

Preserve dedicated source reviews, native replacement/rebuild recipes, manifests,
Cargo locks, benchmark results and exact-installer records. Several docs files are
read or shipped by packaging scripts. A historical experiment can still support a
current resource decision or required provenance; check callers before deleting it.
Keep candidate hashes, source/seed identities, waivers and platform limits intact.
Source/debug checks, UI approval and exact-installer acceptance are separate.

For release/seed work follow the release runbook and the `yomimado-release` skill
when available. Reviewed source, verified private input activation and installer
publication are separate gates. Do not publish or approve an installer without the
owner's explicit authorization. Existing fresh-Mac waivers and untested Windows
hardware cases do not establish acceptance of another installer hash.

## Workflow

Before editing, inspect the existing repository and working tree, read applicable
docs and confirm the requested milestone. Preserve unrelated user changes.

Follow [Git conventions](docs/git-conventions.md): new topic branches use
`<type>/<topic>` with no tool-specific prefix; commits use
`type(scope): imperative summary` (scope optional). Continue the current task's
selected branch for follow-ups to that same task. Give each newly requested feature
or bug fix a dedicated branch; create it from fetched `main` before editing, or
move only the completed task's changes onto it before opening the PR if work has
already started elsewhere. Preserve unrelated changes and published history.
Target PRs to `main`, the only integration branch. `develop` is
retired; preserve its unmerged history during migration. Preserve reviewed seed
and source commit identities when merging; do not rewrite published history.

Main merges run Checks. Merging a same-repository `release/*` PR into main starts
Release, which waits for successful exact-commit Checks before building. Manual
main dispatch remains available for recovery. Installer publication retains the
owner's separate approval.

After editing:

1. Run relevant tests, formatting/lint and a current-target build where practical.
   For documentation-only edits, verify formatting, local links/fragments and
   affected script references; app builds are unnecessary without code changes.
2. Summarize changes, checks and platform limitations without claiming unrun tests.
3. Update implementation status for a completed milestone; put dated changes in
   CHANGELOG and exact release/build evidence in the dedicated records.
4. For material features, fixes or workflow changes, create a focused verified
   commit and push it to the task's branch unless the user says otherwise.
   Stage explicit files, exclude unrelated changes and never force-push. If pushing
   fails, report the local commit and blocker.
5. When a requested feature or bug fix is complete and relevant checks support
   that conclusion, open a PR to `main` automatically from its dedicated branch.
   The user's feature/fix request authorizes opening the PR; do not ask for
   separate approval when confident the work is done. Update an existing PR for
   the same task rather than opening a duplicate. If completion, intended behavior
   or verification is uncertain, first make the implementation and evidence
   reviewable, explain the uncertainty, and ask the user to approve opening the PR.
   Record checks and platform limits in the PR and return its link. Opening a PR
   does not authorize merging it or publishing an installer.

## Documentation maintenance

Keep one canonical home per subject. README introduces the app and links to setup;
installation-guide owns packaged-app installation and first-run setup; usage owns
reading controls; docs/README is the navigation index; implementation-plan owns current status,
roadmap and feature limits; architecture owns runtime structure/resources;
design-system owns visual/native UI contracts; ui-testing owns UI acceptance.
Keep developer commands and debug notes in development, and release procedures in
the release runbook. Keep README installation text brief and link to the full
installation guide rather than repeating its steps.

Keep installation and usage guides focused on current end-user tasks. Put old
version notes, acceptance history and development/debug instructions in their
respective release records, Git history or development guide.

Merge completed short feature notes into the relevant guide. Remove superseded
plans once current behavior and useful evidence have a home. Put chronological
work in CHANGELOG or Git history rather than growing a second implementation
diary. Update inbound links and the index whenever documents move or disappear.
Never discard source/licence or exact-candidate evidence merely to reduce file count.
