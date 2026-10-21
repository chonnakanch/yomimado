# Branch names and commit rules

These are YomiMado's conventions for human contributors and coding agents.
Apply them to new work; existing branch names, commits, tags and release evidence
retain their recorded identities. The rules guide contributions and agent work;
they do not install Git hooks or add a CI naming gate.

## Branches

Task branch names use `<type>/<topic>` without a tool-specific prefix. Release
preparation uses `release/<version>`, for example `release/0.5.0`.

`main` is the only integration branch. It contains completed, checked work for
future releases; published version tags identify released source.

| Branch              | Purpose                                      | Normal PR target               |
| ------------------- | -------------------------------------------- | ------------------------------ |
| `main`              | Protected integration branch.                | Updated through protected PRs. |
| `<type>/<topic>`    | A focused task based on current `main`.      | `main`.                        |
| `release/<version>` | Version preparation; merging starts Release. | `main`.                        |

Use lowercase ASCII letters, numbers and hyphens for `<topic>`. Keep it short and
specific. Use one of the commit types below for `<type>`, or `release` for version
preparation; the branch type describes the task's primary purpose. Do not include spaces, underscores, personal names or
ambiguous descriptions such as `updates`, `stuff` or `final`.

Examples:

```text
feat/kanji-compounds
fix/windows-overlay-position
docs/release-runbook
build/release-notes
release/0.5.0
```

Start new substantial tasks on a topic branch. Continue an existing in-progress
task on its selected tracked branch unless the user requests another branch; do
not move dirty or unrelated changes just to apply the convention. An explicitly
requested branch name takes precedence.

From a clean checkout, create a new task branch from fetched development source:

```sh
rtk git fetch origin
rtk git switch -c feat/kanji-compounds origin/main
```

Push verified work to its existing upstream. For a newly created branch, set its
upstream on the first push:

```sh
rtk git push -u origin feat/kanji-compounds
```

Do not push directly to `main`. Features, fixes and release preparation all use
focused branches and protected PRs into `main`. Merging a same-repository
`release/*` PR starts Release automatically; it waits for Checks on the exact
main commit before building installers. Other PR merges run Checks only. Manual
**Actions → Release → Run workflow → main** remains available for recovery.
Publication retains its separate owner approval. Main does not need a new version for every feature PR; bump the five app
version files together in a release-preparation PR when ready to ship.

`develop` is retired as an integration target. Preserve all of its unmerged work
and any main-only repairs in the migration PR. Retarget outstanding PRs to `main`.
Only remove the old branch after its tip is an ancestor of merged `main` and no
active PR still depends on it; do not force-push or discard its commits.

## Commit messages

Use this header format:

```text
type(scope): imperative summary
```

The scope is optional: `docs: explain runtime seed preparation` is valid. Use a
lowercase type and scope, one space after the colon, and a concise English summary
starting with a verb such as `add`, `fix`, `preserve`, `remove` or `document`.
Keep the header at most 72 characters and omit a trailing period.

| Type       | Use for                                                  |
| ---------- | -------------------------------------------------------- |
| `feat`     | New user-visible behavior                                |
| `fix`      | Correcting faulty behavior                               |
| `perf`     | Improving performance without changing intended behavior |
| `docs`     | Documentation and agent instructions                     |
| `refactor` | Restructuring code without a behavior change             |
| `test`     | Tests and test fixtures                                  |
| `build`    | Build, packaging and release tooling                     |
| `ci`       | CI workflow configuration                                |
| `chore`    | Version preparation and other maintenance                |
| `style`    | Formatting-only changes                                  |
| `revert`   | Reversing an earlier change                              |

Useful scopes include `capture`, `overlay`, `ocr`, `tokenizer`, `dictionary`,
`translation`, `saved`, `ui`, `release`, `deps` and `agent`. Use a scope that helps
identify the affected area; omit it when the change spans several areas.

Examples:

```text
feat(dictionary): show example kanji compounds
fix(overlay): preserve coordinates at 150 percent scaling
perf(ocr): reuse identical recognition crops within a scan
docs(release): explain source review and seed activation
build(release): bind PR notes to the verified candidate
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
  for branches containing reviewed runtime seeds or
  exact-source release evidence. Their pinned source commits must remain in the
  fetched history; squashing or rebasing them can invalidate reuse/source checks.
- Squash or rebase only unpublished, unreviewed work when no pinned candidate,
  source approval or other contributor depends on the original commits. Do not
  force-push shared branches or rewrite published history to fix message style.
- Before any main merge, require passing Checks for the current PR base. For a
  version-preparation PR, also complete the
  [release preparation checklist](desktop-release.md#prepare-each-new-release-before-merging-main).
  Ordinary feature/fix PRs do not need a version bump. Main integration and
  installer publication retain their separate authorization.

Checks runs on pushes to `main`, PRs targeting `main` and manual runs. Its
required `gates` covers frontend, service, release-tool and both native-platform
jobs. Release starts for a merged same-repository `release/*` PR into `main`, or
a manual main dispatch, and waits up to 15 minutes for successful GitHub Actions
`gates` for its exact source before private input access. Closed unmerged PRs,
feature/fix merges and fork release branches cannot start builds. Keep main at the
selected candidate until publication; an advanced main is still rejected.

## Release-note compatibility

Public release notes list GitHub PR titles and numbers since the previous app
release, followed by a Full Changelog comparison. Use descriptive titles and merge
features through PRs into `main` so they have individual entries; direct commits
have no invented PR number. Review titles and reverts before publication approval.
The Full Changelog comparison includes direct commits. Naming rules do not justify
rewriting old commits or dropping history. Installation belongs in the [installation guide](installation-guide.md); verification
records and limitations stay in the release checklist and metadata. The [release-note procedure](release-runbook.md#generate-and-review-release-notes)
preserves the existing publication gates.
