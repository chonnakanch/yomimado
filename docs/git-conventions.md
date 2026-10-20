# Branch names and commit rules

These are YomiMado's conventions for human contributors and coding agents.
Apply them to new work; existing branch names, commits, tags and release evidence
retain their recorded identities. The rules guide contributions and agent work;
they do not install Git hooks or add a CI naming gate.

## Branches

Task branch names use `<type>/<topic>` without a tool-specific prefix.

| Branch           | Purpose                                                       | Normal PR target                             |
| ---------------- | ------------------------------------------------------------- | -------------------------------------------- |
| `main`           | Protected release source; a push starts the Release workflow. | Updated through a protected PR.              |
| `develop`        | Integration branch for completed development work.            | `main` when preparing an authorized release. |
| `<type>/<topic>` | A focused task, based on current `develop`.                   | `develop`.                                   |

Use lowercase ASCII letters, numbers and hyphens for `<topic>`. Keep it short and
specific. Use one of the commit types below for `<type>`; the branch type describes
the task's primary purpose. Do not include spaces, underscores, personal names or
ambiguous descriptions such as `updates`, `stuff` or `final`.

Examples:

```text
feat/kanji-compounds
fix/windows-overlay-position
docs/release-runbook
build/git-cliff-notes
chore/release-0-4-0
```

Start new substantial tasks on a topic branch. Continue an existing in-progress
task on its selected tracked branch unless the user requests another branch; do
not move dirty or unrelated changes just to apply the convention. An explicitly
requested branch name takes precedence.

From a clean checkout, create a new task branch from fetched development source:

```sh
rtk git fetch origin
rtk git switch -c feat/kanji-compounds origin/develop
```

Push verified work to its existing upstream. For a newly created branch, set its
upstream on the first push:

```sh
rtk git push -u origin feat/kanji-compounds
```

Do not push directly to `main`. A main-targeted urgent fix may branch from
`origin/main` when that is the requested scope; it still uses the protected PR,
version, seed-compatibility and release checks. Bring the resulting fix back into
`develop` so a subsequent release retains it.

## Commit messages

Use this header format:

```text
type(scope): imperative summary
```

The scope is optional: `docs: explain runtime seed preparation` is valid. Use a
lowercase type and scope, one space after the colon, and a concise English summary
starting with a verb such as `add`, `fix`, `preserve`, `remove` or `document`.
Keep the header at most 72 characters and omit a trailing period.

| Type       | Use for                                                  | git-cliff group   |
| ---------- | -------------------------------------------------------- | ----------------- |
| `feat`     | New user-visible behavior                                | Features          |
| `fix`      | Correcting faulty behavior                               | Fixes             |
| `perf`     | Improving performance without changing intended behavior | Performance       |
| `docs`     | Documentation and agent instructions                     | Documentation     |
| `refactor` | Restructuring code without a behavior change             | Maintenance       |
| `test`     | Tests and test fixtures                                  | Maintenance       |
| `build`    | Build, packaging and release tooling                     | Maintenance       |
| `ci`       | CI workflow configuration                                | Maintenance       |
| `chore`    | Version preparation and other maintenance                | Maintenance       |
| `style`    | Formatting-only changes                                  | Maintenance       |
| `revert`   | Reversing an earlier change                              | Reverts to review |

Useful scopes include `capture`, `overlay`, `ocr`, `tokenizer`, `dictionary`,
`translation`, `saved`, `ui`, `release`, `deps` and `agent`. Use a scope that helps
identify the affected area; omit it when the change spans several areas.

Examples:

```text
feat(dictionary): show example kanji compounds
fix(overlay): preserve coordinates at 150 percent scaling
perf(ocr): reuse identical recognition crops within a scan
docs(release): explain source review and seed activation
build(release): add pinned git-cliff note generation
ci(release): verify runtime compatibility before merge
chore(release): prepare v0.4.0
revert(ocr): remove bubble retry actions
```

For a material change, explain the concrete problem and resulting behavior in the
body when the header is insufficient. Record relevant validation and platform
limits without claiming unperformed tests. A revert body should identify the
original commit and explain what behavior is restored. Reference an issue or PR
when it supplies useful context.

For a breaking API, data-format or supported-workflow change, place `!` before
the colon and describe the impact and required migration in a `BREAKING CHANGE:`
footer. Do not use it for an ordinary bug fix. This is a review signal; it does
not automatically choose an app version or approve a release.

```text
feat(ocr)!: change the OCR response schema

BREAKING CHANGE: explain the removed fields and how callers must migrate.
```

## Commit and merge discipline

- Keep each commit focused on one logical change. Include the implementation,
  relevant tests and necessary documentation together. Separate unrelated cleanup.
- Review the diff and run applicable checks before committing. Stage explicit
  files or hunks; keep unrelated user changes out of the commit. For material
  work, create a focused commit and push to the task's tracked branch unless the
  user asks otherwise, as required by `AGENTS.md`.
- Preserve the five app version files as one consistent version update. Commit
  the intended version/code before generating notes from that commit. Follow the
  [release runbook](release-runbook.md) for source review and acceptance records.
- Use a descriptive PR title in the same commit-header format. State the problem,
  resulting behavior, relevant checks and material limitations in the PR body.
- Prefer merge commits for task integration. Use a merge that preserves commits
  for `develop` → `main` and for branches containing reviewed runtime seeds or
  exact-source release evidence. Their pinned source commits must remain in the
  fetched history; squashing or rebasing them can invalidate reuse/source checks.
- Squash or rebase only unpublished, unreviewed work when no pinned candidate,
  source approval or other contributor depends on the original commits. Do not
  force-push shared branches or rewrite published history to fix message style.
- Before a main merge, require passing Checks for the current PR base and the
  [release preparation checklist](desktop-release.md#prepare-each-new-release-before-merging-main).
  Main integration and installer publication retain their separate authorization.

Checks currently runs on pushes to `develop`/`main` and on PRs targeting `main`.
A topic PR targeting `develop` does not itself receive that workflow under the
current triggers. Run its applicable local checks before integration and inspect
the develop push run afterward; do not describe an unrun PR check as passed.

## Release-note compatibility

The types above match [`cliff.toml`](../cliff.toml). git-cliff still includes older
or unconventional commits under a matching group or **Other changes**; new naming
rules do not justify dropping history or rewriting old commits.

Public release notes list GitHub PR titles and numbers since the previous app
release, followed by a Full Changelog comparison. Use descriptive titles and merge
features through PRs into `develop` so they have individual entries; direct commits
have no invented PR number. Review titles and reverts before publication approval.
The optional git-cliff audit still inventories every commit. Installation belongs
in README; verification records and limitations stay in the release checklist and
metadata. The [release-note procedure](release-runbook.md#generate-and-review-release-notes)
preserves the existing publication gates.
