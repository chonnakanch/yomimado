# Manual releases and macOS runtime seeds

Use this runbook for a new version or replacement macOS runtime seed. It describes
the checked-in workflow, not the live status of a GitHub run. Read the current
[implementation status](implementation-plan.md) and [release checklist](desktop-release.md)
before acting. Historical approvals and installer hashes apply only to their
recorded candidates.

## Ask an agent to follow this procedure

The personal Codex skill is `$yomimado-release`. Example requests:

> Use $yomimado-release to prepare version 0.4.0 on develop. Check whether the
> existing macOS seed can be reused, update the release notes, and run the relevant
> checks. Do not merge into main or publish.

> Use $yomimado-release to prepare a replacement macOS runtime seed for the current
> committed develop source. Build and verify the local candidate and prepare the
> complete source/licence delivery for my review.

> Use $yomimado-release to activate the source-approved seed and its verified
> private draft inputs, then prepare the main PR. Do not merge or publish.

An agent without the installed skill can use:

> Follow docs/release-runbook.md and AGENTS.md for this release task. Prepare
> version 0.4.0 on develop, check runtime-seed compatibility, and stop before
> main integration or publication.

Replace the example version and requested scope. Existing user authorization
continues to apply; do not ask again for an already authorized step. Preparing a
seed, approving its source delivery, merging main, accepting exact installers and
approving publication are different actions.

## Decide whether a new seed is needed

The macOS seed supplies the frozen Python service and its runtime/resources.
Release rebuilds the React/Rust desktop app from merged main, but copies this
frozen service rather than freezing the current Python sources again.

| Change                                                                  | Seed decision                                                 |
| ----------------------------------------------------------------------- | ------------------------------------------------------------- |
| App version only                                                        | Reuse the existing seed.                                      |
| React UI or ordinary Rust capture/overlay code                          | Usually reusable; run the guard.                              |
| Packaged Python OCR, tokenizer, lookup, translation or persistence code | Prepare a new seed.                                           |
| macOS Python/native dependencies, models or dictionary inputs           | Prepare a new seed and review changed source/data terms.      |
| Runtime build/freeze recipes or relevant notices                        | Review the changed inputs; normally a new seed is required.   |
| Dependency locks or app build configuration                             | The guard compares more than versions; inspect any rejection. |

From the repository root, after committing the intended changes:

```sh
rtk git status --short --branch
rtk python3 scripts/macos-ci-release.py verify-reuse
```

The guard compares committed `HEAD` with `SEED_REVISION`; it does not inspect
uncommitted edits or prove that an uploaded seed is valid. Read the named rejected
path. Do not change the revision pin or widen allowlists merely to make the guard
pass. A documented, narrowly reviewed runtime-independent exception is different
from approving new frozen inputs. The seed version need not match every later
app version when its runtime remains compatible.

Checks also runs `plan` and `verify-reuse` with full Git history in its
`release-tools` job. The required `gates` depends on that job: runtime/source
incompatibility must be resolved before a main PR can pass Checks. This step is
read-only and does not download private inputs. The
[0.4.0 frontend-data review](macos-runtime-reuse-0.4.0.md) documents one exact,
hash-pinned runtime-independent exception; it does not permit arbitrary data,
notice or frozen-service changes.

## Release a new app version

Use the [branch and commit rules](git-conventions.md), for example
`chore/release-0-4-0` and `chore(release): prepare v0.4.0`. Integrate a release
topic into `develop` before the protected `develop` → `main` PR, or continue the
already selected integration branch. Preserve the exact reviewed seed/source
commits when merging.

1. Start on an up-to-date `develop` with a clean working directory and intended
   changes committed. Preserve unrelated work. Use Python 3.11 or newer.
2. Preview and update all five app version files together. These commands use an
   example version, without `v`:

   ```sh
   rtk python3 scripts/update_version.py 0.4.0 --dry-run
   rtk python3 scripts/update_version.py 0.4.0
   ```

   Review and commit the intended version/code changes before selecting `HEAD`
   for the draft: the generator reads the version from the committed source.

3. [Generate and review a git-cliff draft](#generate-and-review-release-notes)
   for the previous published tag through the proposed release commit. For example,
   after committing the version/code changes, run from the repository root:

   ```sh
   rtk python3 scripts/release_notes.py prepare
   rtk python3 scripts/release_notes.py generate \
     --previous-tag v0.3.0 \
     --revision HEAD \
     --output services/ocr/build/release-notes/0.4.0-draft.md
   ```

   Replace the previous tag with the actual previous published release and choose
   a new draft filename. Review every group, including reverts, against the final
   code diff and changelog. Then update
   [release notes](desktop-release-notes.md) with only the net changes since that
   previous published release. Replace the previous highlights instead of appending
   another version's section; keep one `## Changes in VERSION` section. Retain
   `VERSION` and `CLASSIFICATION` placeholders and installation/source notices. Review the diff,
   run relevant checks, commit and push focused changes. Run the seed guard against
   the committed source. If it rejects frozen inputs, complete the seed procedure
   before main integration.

4. Prepare the protected `develop` → `main` PR. Merge when authorized and required
   checks pass. A main push starts **Release** automatically. To dispatch manually,
   use **Actions → Release → Run workflow → main**; there is no version input.
5. Confirm **Checks / gates** for that exact main commit, both builders and
   `verify-transfer`. Download `verified-desktop-candidate` before expiry.
6. Verify delivery hashes and test both exact installers using the
   [macOS](macos-clean-mac-test.md) and [Windows](windows-installed-test.md)
   checklists. Record hashes, results, waivers and untested cases without
   converting automated checks into human acceptance.
7. After the owner's explicit publication approval, the owner reviews the
   `desktop-release` deployment. The protected publisher creates the version tag,
   uploads a private draft, verifies it and makes it public. Keep main at the
   tested source through publication: an advanced main is rejected.
8. Confirm the public tag/source/classification and complete asset hashes, then
   update the implementation/release evidence without rewriting historical records.

`0.x.x` and `alpha.N`/`beta.N`/`rc.N` versions are pre-releases; unsuffixed `1.0.0`
and later are stable. Do not create the public version tag ahead of the publisher.
A published version is skipped; an existing incomplete tag/draft requires
investigation. Do not delete/move tags, overwrite assets or blindly retry a
partially completed publisher. Rerunning an old failed job uses its old workflow;
a merged workflow repair requires a new source-bound run.

The current optional-component delivery uses nine uploaded files: two installers,
two platform source archives, combined notices, checksums, provenance and two
translation ZIPs. Follow the candidate's validated layout; older layouts remain
historical. GitHub's automatic repository source links do not replace dependency
source delivery.

## Generate and review release notes

The repository uses **git-cliff 2.14.2** as a standalone maintainer tool. Python
3.11+ prepares its checksum-pinned executable outside the app and OCR runtime:

```sh
rtk python3 scripts/release_notes.py prepare
```

On Windows, use `rtk py -3.11` in place of `rtk python3`. Preparation is the explicit
network/download step. If the interpreter has no configured CA bundle, point
`SSL_CERT_FILE` to an existing trusted certifi bundle; keep TLS verification
enabled. Generation uses only the prepared tool and local Git history.

Fetch current history/tags if necessary, then select the previous **published app
release** yourself, including a pre-release when appropriate. Do not use a private
seed tag, an unpublished candidate tag or GitHub's stable-only latest endpoint.
The example below assumes `v0.3.0` is that release and the committed `HEAD` contains
the intended changes/version:

```sh
rtk git fetch origin --tags
rtk python3 scripts/release_notes.py generate \
  --previous-tag v0.3.0 \
  --revision HEAD \
  --output services/ocr/build/release-notes/0.4.0-draft.md
```

The wrapper reads the app version at the selected commit and records the exact
previous/target SHAs, commit count and comparison link. It requires full history,
an existing release tag ancestral to the target, a nonempty range and a new output
path. Existing files are never overwritten. A tag, release, approval or version
bump is not created by this command.

`cliff.toml` groups every commit, including unconventional messages, merge commits
and reverts. The wrapper compares git-cliff's context against `git rev-list` and
checks rendered commit links; omissions or duplicates fail before writing. This
is a complete commit inventory, not an automatic claim about available features.

Review it against the final diff and [CHANGELOG.md](../CHANGELOG.md). Summarize the
net features, fixes, removals and relevant dependency changes in the curated
[release notes](desktop-release-notes.md). That file is the current release's
publication body, not a cumulative changelog: replace its highlights with the net
changes since the selected previous published tag, keeping only one
`## Changes in VERSION` section. Older changes remain in historical GitHub releases
and Git history; preserve `CHANGELOG.md` as the historical log. In particular, an added-then-reverted
feature belongs in the review history, not in available features. Keep known
limitations, `VERSION`/`CLASSIFICATION` placeholders and installation/source/data
notices. Do not overwrite the historical changelog with raw generated entries.

If the selected source changes, generate a new draft with a new output filename.
The protected publisher still uses the reviewed notes file and appends candidate
source/download hashes. See the [tool/version licence record](../THIRD_PARTY_LICENSES/git-cliff/README.md).

## Build a replacement macOS seed

### 1. Fix the source revision and local inputs

Use an Apple Silicon Mac with Xcode command-line tools, Node/npm and the pinned
Rust toolchain from [Release](../.github/workflows/release.yml). Read the
[macOS build guide](macos-release.md), [source review](macos-source-review.md) and
[current seed record](macos-runtime-seed.md).

Commit intended runtime, dependency, notice and build changes first. The project
and detector checkouts must be clean and remain at their selected revisions.
Do not mix a DMG with sources/notices from another build. Keep old seed files and
records; preparation outputs are ignored local data.

From the repository root, keep these variables in the same shell for the examples:

```sh
yomi_root="$PWD"
yomi_seed_revision="$(rtk git rev-parse HEAD)"
yomi_seed_short="$(rtk git rev-parse --short=7 HEAD)"
yomi_seed_version="$(rtk python3 -c 'import json; print(json.load(open("apps/desktop/package.json"))["version"])')"
yomi_seed_work="$yomi_root/services/ocr/build/runtime-seed-$yomi_seed_short"
yomi_python="$yomi_root/services/ocr/build/release-venv/bin/python"
yomi_notices="$yomi_root/apps/desktop/src-tauri/resources/ocr/notices"
yomi_source_dir="$yomi_seed_work/source-delivery-$yomi_seed_short"
rtk mkdir -p "$yomi_root/services/ocr/build"
rtk mkdir "$yomi_seed_work"
rtk mkdir "$yomi_seed_work/candidates"
```

Use a new work directory for a new attempt rather than overwriting evidence.
Supply the pinned local detector checkout, Manga OCR snapshot, translation model
input, JMdict and KANJIDIC2 described in the build guide. Translation model input
is still needed to generate its separate optional ZIP. The smoke-only detector
ONNX file stays outside the installer/source archives. Use no user manga in
public fixtures or source delivery.

### 2. Prepare the environment and freeze a private candidate

For a fresh environment or changed runtime/dependency inputs:

```sh
rtk bash scripts/build-macos-prerelease.sh --prepare-runtime
rtk bash scripts/build-macos-prerelease.sh --prepare-native
```

The first command builds the pinned Python/native environment in `release-venv`;
the development `.venv` is separate. If only packaged app Python code changed,
reuse an existing environment only when its lock/build-input verification passes.

Install locked desktop dependencies if needed, then generate the actual frozen
runtime and inventory:

```sh
rtk npm ci --prefix apps/desktop
rtk bash scripts/build-macos-prerelease.sh
```

This is a private candidate, not a source-approved seed. Preserve generated native
build records and original source archives. Resolve lock, model, platform, import
or bundle verification failures before continuing.

### 3. Collect sources and create the unsigned worksheet

```sh
rtk cargo vendor --locked \
  --manifest-path apps/desktop/src-tauri/Cargo.toml \
  "$yomi_seed_work/candidates/cargo-vendor"

rtk "$yomi_python" scripts/prepare-macos-sources.py \
  "$yomi_notices" "$yomi_seed_work/candidates" \
  --cargo-vendor "$yomi_seed_work/candidates/cargo-vendor"

rtk "$yomi_python" scripts/macos-release.py source-template \
  "$yomi_notices" --revision "$yomi_seed_revision" \
  > "$yomi_seed_work/candidates/source-delivery.worksheet.json"
```

The collector writes `source-candidates.json`, not a completed worksheet or an
approval. Inspect its `unresolved` entries even if the command succeeds. Populate
every worksheet component with the actual archive, hash, source/licence evidence
and notice paths. Supply `BUILD.md`, native notice supplements and any referenced
build instructions. Reuse previous technical evidence only when its source,
binary and notice hashes still match. Leave `reviewer` and `reviewedAt` blank.

### 4. Assemble and inspect the complete delivery

```sh
rtk "$yomi_python" scripts/prepare-macos-sources.py \
  "$yomi_notices" "$yomi_seed_work/candidates" \
  --assemble-delivery "$yomi_source_dir"
```

The destination must be new. Assembly filters source assets, records omissions
and original/delivery hashes, and writes another unsigned worksheet. It copies
referenced archives; separately carry across the reviewed `BUILD.md`, native
notice supplements and other required instructions. Do not replace Cargo cache
archives with filtered delivery archives.

Verify complete component/native coverage, exact project/frozen service source,
archive contents, retained preferred code/notices and documented omissions. Record
how frozen modules were compared with the selected source and retain the report.
Disclose unverified source-only rebuilds and unresolved dependency advisories.
Prepare the complete delivery and technical report before requesting the owner's
source/licence approval.

After actual approval, retain the unsigned worksheet and create the separate
`source-delivery.json` with the approved manifest, reviewer, date and scope. Do
not invent approval, copy it from another revision or treat this as installer
acceptance/publication approval. If the delivery adds `native-notices/`, copy that
reviewed supplement into the generated `$yomi_notices/native-notices/` before
validation, as the release build does. Validate against the matching inventory:

```sh
rtk "$yomi_python" scripts/macos-release.py verify-sources \
  "$yomi_notices" --source-dir "$yomi_source_dir" \
  --revision "$yomi_seed_revision"
```

### 5. Build and verify the source-approved seed

Replace the example detector path with the separately installed, pinned ONNX file:

```sh
YOMIMADO_SOURCE_DIR="$yomi_source_dir" \
YOMIMADO_SMOKE_DETECTOR_MODEL="/absolute/path/comictextdetector.pt.onnx" \
rtk bash scripts/build-macos-prerelease.sh --release
```

The hobby path needs no Apple signing account. It seals the app with ad-hoc
signatures and checks mounted platform/bundle/source/signature and frozen offline
learning/persistence behavior. It remains unnotarized. Record successful checks
and limits rather than treating these as Finder/Gatekeeper/Screen Recording or
final CI installer acceptance.

Only successful candidates are copied to
`apps/desktop/src-tauri/target/release/bundle/releasable/`. Ensure the source
revision/inventory did not change. Preserve that exact DMG and matching source,
notice, module-comparison and smoke reports.

### 6. Package and stage the private inputs

Create a new seed input directory and matching archives after all checks pass:

```sh
rtk mkdir "$yomi_seed_work/seed-inputs"
rtk cp "apps/desktop/src-tauri/target/release/bundle/releasable/YomiMado_${yomi_seed_version}_aarch64.dmg" \
  "$yomi_seed_work/seed-inputs/"
rtk tar -czf "$yomi_seed_work/seed-inputs/YomiMado_${yomi_seed_version}_sources_${yomi_seed_short}.tar.gz" \
  -C "$yomi_seed_work" "source-delivery-$yomi_seed_short"
rtk tar -czf "$yomi_seed_work/seed-inputs/YomiMado_${yomi_seed_version}_notices_${yomi_seed_short}.tar.gz" \
  -C "${yomi_notices%/notices}" notices
rtk cp "services/ocr/build/translation-components/YomiMado_${yomi_seed_version}_translation_torch.zip" \
  "$yomi_seed_work/seed-inputs/"
rtk shasum -a 256 "$yomi_seed_work/seed-inputs/"*
```

Validate archive membership, paths and hashes; confirm the source archive includes
the approved manifest and every referenced file. Check the translation ZIP
against the embedded `translation-component.json`, not its filename alone.
Each uploaded input must be smaller than the existing 2 GiB limit. Keep the hash,
size, revision and approval-scope report outside the exact input directory.

When staging is authorized, save an **unpublished GitHub draft** using the label
`macos-reviewed-seed-<shortSHA>` and the exact seed commit as its target. Upload
only the four inputs above. Verify Draft status, target/label, exact membership,
uploaded state, sizes and GitHub SHA-256 values against local bytes. Do not create
the public app version tag or publish the seed. Retain old drafts and evidence.

### 7. Activate the verified inputs together

Update all three consumers on the release preparation branch:

| File                            | Change                                                                                                  |
| ------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `scripts/macos-ci-release.py`   | Set `SEED_REVISION` to the full approved source commit.                                                 |
| `scripts/desktop_release.py`    | Set macOS `INPUTS` to the private draft label and exact four filenames/hashes.                          |
| `.github/workflows/release.yml` | Update seed DMG/source/notice filenames, extraction directory, `YOMIMADO_SOURCE_DIR` and cleanup paths. |

Use the source archive's actual top-level `source-delivery-<shortSHA>` directory.
Do not change Windows dictionary pins unless that separate input changes.
Do not set the seed revision to the later activation commit: it identifies the
actual approved runtime source. Commit the activation changes and run the guard
against that committed state.

Verify the staged inputs with the updated pins:

```sh
rtk python3 scripts/desktop_release.py verify-inputs \
  --platform macos --directory "$yomi_seed_work/seed-inputs"
rtk python3 scripts/macos-ci-release.py verify-reuse
```

Run applicable existing release-tool suites (`test_macos_release.py`,
`test_macos_sources.py`, `test_macos_notices.py`, `test_desktop_release.py`,
`test_release_rules.py`, `test_update_version.py`), script Ruff checks and pinned
actionlint for workflow changes. Use the existing CI/release verification
environment; do not mutate the reviewed runtime to install test tools. Run
service/frontend/native checks when those inputs changed.

Add the new review, exact hashes, uploaded verification and remaining limits to
[the seed record](macos-runtime-seed.md) and implementation status. Preserve
previous records. With authorized main integration, return to the normal release
procedure. A new release build creates new installer hashes even with this seed.

## Evidence to hand back

Report the selected version/commit, reuse decision and changed paths, exact local
and uploaded input identities/hashes, source approval scope, checks actually run,
remaining platform limitations, current commit/PR/run and next authorized step.
State a missing approval or failed boundary precisely. A ready local seed does
not imply that staging, main integration or publication occurred.
