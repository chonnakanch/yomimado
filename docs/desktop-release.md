# Shared desktop release checklist

Published — 2026-10-12: [YomiMado v0.1.0](https://github.com/chonnakanch/yomimado/releases/tag/v0.1.0)
is a public **pre-release** for macOS Apple Silicon and Windows 11 x64 CPU.
The owner approves recovery [run `38257468295`](https://github.com/chonnakanch/yomimado/actions/runs/38257468295)
at repair executor `a30d0ba`; its read-only gate passes in 6m 10s and protected
publisher passes in 1m 9s. It publishes the existing exact draft by ID after
all uploaded hashes verify. The tag remains at the tested application source
`5159473da21c952f1a4dc87c457bba82edf5edde`; no installer/tag/assets are rebuilt,
replaced or moved. Both exact-hash local installer reports pass.

Independent public API verification confirms title, pre-release classification,
original source target and all **17 uploaded asset names/states/SHA-256 digests**
match the original CI candidate. Publicly downloaded combined provenance and
checksum bytes match their pinned hashes. The two GitHub-generated source links
bring the web page's Assets count to 19; the verified uploaded delivery is 17.
Fresh-Mac waiver, untested Windows hardware and the unverified full source-only
rebuild remain disclosed. Archived build flags are unchanged; the protected
owner reviews record human approval separately.

Historical publication failure — 2026-10-12: after protected owner review, run
`38201230907` creates `v0.1.0` at the tested `5159473` source and uploads the
17 delivery files to a private **YomiMado v0.1.0** pre-release draft. The next
`GET /releases/tags/v0.1.0` request fails with HTTP 404 because the draft is
unpublished. The release remains private at `untagged-e301a488f7929f16aa3d`;
the tag already exists. Both exact installers' passing results remain valid.

Focused [PR #4](https://github.com/chonnakanch/yomimado/pull/4), source `13ce1bb`,
resolves drafts through the complete release listing
and verifies/publishes by ID. A separately protected, one-candidate recovery
preserves the existing tag/assets and the same passed installer bytes. Its
strict repair scope rejects app/runtime changes and unrelated develop cleanup.
See [the recovery checks and owner steps](desktop-release-recovery.md).
All 233 develop tests and 231 isolated-main release-tool tests, lint/format,
actionlint and Mac runtime scope checks pass. The owner separately authorizes
PR #4 and recovery dispatch; it merges at
`a30d0ba2b931ab9443b656b64ed55ba7a1d9ffc0`. Only the nine explicit release
repair files differ from the tested source. Recovery
[run `38257468295`](https://github.com/chonnakanch/yomimado/actions/runs/38257468295)
passes its read-only automatic gate in **6 minutes 10 seconds**, including the
original ZIP/record/17-file hashes, existing tag, original successful builders,
current main/environment protection and unchanged app/runtime scope. Its
protected publisher subsequently passes in 1m 9s after the owner's new review.
Installer bytes and local passes are unchanged; recovery is complete. Do not rerun the old publisher or delete/move the tag or draft.

Latest rollout — 2026-10-12: the owner explicitly authorizes [PR #3](https://github.com/chonnakanch/yomimado/pull/3),
merged at `5159473da21c952f1a4dc87c457bba82edf5edde`. Both required PR checks
pass; the new main [gate run `38201230971`](https://github.com/chonnakanch/yomimado/actions/runs/38201230971)
passes. [Joint build `38201230907`](https://github.com/chonnakanch/yomimado/actions/runs/38201230907)
passes all automatic jobs: **Windows 36 minutes 18 seconds**, **macOS 12 minutes
16 seconds**, combined verification **1 minute 34 seconds**. The protected
publisher subsequently runs after owner review and fails at the draft lookup,
as recorded above. Publisher-only
concurrency is deployed, so the older waiting review does not hold later builds.
Main has advanced: candidate `99b1312` is superseded and its publication job must
not be approved. The latest exact DMG passes the existing-Mac installed gate
with explicit maintainer confirmation and independently verified download
hashes. The maintainer reports all six Windows checks pass and explicitly
confirms setup SHA-256 `a8275246…`. Both current exact-installer local gates are
complete. The release remains private after the original protected publication
review and failed lookup. The repair needs separate merge authorization and
new protected recovery review; it proposes no installer rebuild or retest.

Original build delivery — [verified-desktop-candidate](https://github.com/chonnakanch/yomimado/actions/runs/38201230907/artifacts/11726850805),
artifact `11726850805` (4.06 GB), retained for 14 days from this run. GitHub's
artifact ZIP SHA-256:
`a6eec1b72e614ba45d30e9fe0651bb079b6266df0db5a4871e55bc896a5be91a`.
The hosted gate verifies all 17 combined files, source
`5159473da21c952f1a4dc87c457bba82edf5edde`, version `0.1.0` and pre-release
classification. Exact installer hashes:

| Installer                      | SHA-256                                                            |
| ------------------------------ | ------------------------------------------------------------------ |
| `YomiMado_0.1.0_x64-setup.exe` | `a8275246dc07a30f84a2109530bd68c3c0cceeed2556ce27fb09681d3a404602` |
| `YomiMado_0.1.0_aarch64.dmg`   | `9d2999ae49b1756d23e62e6b703284e1d5c87898dc187757dfa3d881b8b28977` |

GitHub summary/transfer hashes are verified. All seven downloaded Mac candidate
files independently verify against the CI-bound provenance and hashes. The
maintainer reports the expected unnotarized-app Gatekeeper warning, then
confirms working launch and every explicitly listed Mac functional check:
OCR/page scan, shortcut, dictionary/kanji, new offline translation and saved
data/model persistence after restart/reboot. The existing-Mac gate passes;
fresh-Mac and unreported detailed subcases remain untested. The maintainer also
confirms the Windows setup download hash and all six local checklist groups.
Independent agent inspection of the Windows/combined ZIP has not been performed
locally. The hosted transfer gate verifies all 17 files, source/notice bindings,
version/classification and hashes; the protected publisher rechecks the exact
files and GitHub upload digests before publication. That local-copy limitation
does not replace or weaken these enforced verification gates.

Both [the six Windows checks](windows-installed-test.md) and
[the existing-Mac installed gate](macos-clean-mac-test.md) pass for the current
hashes. Fresh-Mac testing remains waived. Only the owner may approve
**this run's** publisher after reviewing the exact candidate; do not approve the
superseded run. Download before the artifact's retention expires.
The version tag now exists; the release remains a private draft.

Historical preparation — 2026-10-11 on `develop`. The maintainer confirms the private Windows
setup SHA-256 `756b7dc6003af202e4df95e946edcbc7fe409c41cfd0d2fc3be4062f758b4a1b`
and all six local checklist groups pass. Actual Windows native inputs, delivered
sources/notices, owner Community 2022 confirmation and component-terms checks
are recorded separately from macOS clearance. Protected publication approval
remains open. The owner authorized [PR #1](https://github.com/chonnakanch/yomimado/pull/1)
and it merged at `ffd1acc2c4a241864143fca61195e849cd8f1893`. No public version
tag or release has been created.

First main execution — [run `38157096085`](https://github.com/chonnakanch/yomimado/actions/runs/38157096085):
planning and automatic private input transfer pass. The Windows builder passes
every automated gate in **43 minutes 6 seconds**; its setup SHA-256 is
`4d9a57ab67e947842abe433b33db0155a1ea36f08b4d3e9825fdc341cbc7ab2f`.
These new bytes have not been locally approved. The macOS builder stops during
bootstrap because GitHub does not provide Python 3.11.17 for Darwin arm64.
Combined verification and publication are skipped. The repair pins verification
tools to the available **3.11.9 arm64** entry in
[GitHub's Python manifest](https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json);
the exact reviewed **3.11.17 frozen runtime** still comes from the hash-pinned seed.
Repair rollout — the owner explicitly authorizes **PR #2 only**, merged at
`99b13124424901f425a49de7ed87557eee6230a9`. Main gate checks pass in
[run `38196721793`](https://github.com/chonnakanch/yomimado/actions/runs/38196721793).
The automatic joint [run `38196721752`](https://github.com/chonnakanch/yomimado/actions/runs/38196721752)
passes every automatic job: macOS in **14 minutes 37 seconds**, Windows in
**39 minutes 17 seconds**, and combined verification in **1 minute 21 seconds**.
Both builders run without approval. The protected publisher is waiting; no
public version tag or release has been created. Subsequent repair merges are
not authorized by this PR #2 confirmation. Publication approval remains
reserved to the owner.

Superseded private delivery — [verified-desktop-candidate](https://github.com/chonnakanch/yomimado/actions/runs/38196721752/artifacts/11724359701),
artifact `11724359701` (4.06 GB), retained for 14 days from this run. GitHub's
artifact ZIP SHA-256 is
`dbc7285933b3f02883e9a3d4b4081d6ea1545581fd7edd815c93439597599eb9`.
The hosted combined gate verifies all 17 files against source
`99b13124424901f425a49de7ed87557eee6230a9`, version `0.1.0` and pre-release
classification. Its summary records these exact installers:

| Installer                      | SHA-256                                                            |
| ------------------------------ | ------------------------------------------------------------------ |
| `YomiMado_0.1.0_x64-setup.exe` | `e57ef7e9282023afcff540af86c48d4fb1a97ca42f6ee8932495a534bdfaa8cd` |
| `YomiMado_0.1.0_aarch64.dmg`   | `dda5ba255c21d70276d082551f73636628548fad85c8be5d8cd7c830e2726c98` |

These are GitHub job-summary/transfer results, not an independent local download
verification. Local artifact/checksum inspection and both exact-installer
checklists remain pending. The maintainer reports the Windows PC is available
later; keep this candidate private. Previous passing installers have different
bytes. Download before artifact expiry; an expired artifact requires a new
build and a new exact-hash report. Fresh-Mac testing remains waived.

Follow-up merged through authorized PR #3: serialize only the **publish** job,
rather than the whole workflow. A pending installer review must not queue subsequent
main builds. Publisher uploads remain non-cancellable and serial; current-main
and absent-tag checks still reject stale candidates and collisions. This repair
does not change app/runtime inputs. The owner supplied its separate merge
authorization; protected publication approval remains separate.

Historically, `macos-prerelease.yml` was named **Desktop release from main** and
replaced the macOS-only publisher with one shared publisher/tag. It is now
[release.yml](../.github/workflows/release.yml), displayed as **Release**.
The separate Windows development candidate is retired; both installers are
built and verified by Release on protected main.

## Future release asset layout

Routine workflow cleanup — the five standalone Windows audit/probe workflows,
completed one-candidate v0.1.0 recovery and separate Windows private candidate are
[archived outside Actions discovery](workflow-history/README.md). Two routine
definitions remain: **Release** (`release.yml`) and **Checks** (`checks.yml`).
The required main status context remains `gates`. Packaging scripts and historical
source/licence/test evidence are preserved. Retirement is prepared on `develop`
for a future authorized main merge; no release assets or run history are deleted.

Future shared releases package **six uploaded files**:

| File                                | Contents                                                                                                     |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `YomiMado_<version>_aarch64.dmg`    | Direct macOS installer download                                                                              |
| `YomiMado_<version>_x64-setup.exe`  | Direct Windows installer download                                                                            |
| `YomiMado_<version>_sources.tar.gz` | Original macOS source delivery, Windows dependency sources/recipes, project sources and dictionary snapshots |
| `YomiMado_<version>_notices.tar.gz` | Original platform notice archives, native input inventory, platform records and checksum sidecars            |
| `desktop-SHA256SUMS.txt`            | Hashes of the five other uploaded files                                                                      |
| `desktop-release-candidate.json`    | Shared identity, public file hashes, original input hashes and both platform candidate records               |

The builders retain their existing platform outputs and verification. The shared
transfer job verifies those outputs before consolidation. Each combined archive
contains a `README.txt` and `macos/` or `windows/` files; extract the outer archive,
then the original platform archives to obtain their unchanged internal paths and
build recipes. All 15 original platform files are retained, either as direct
installers or inside the archives. No source/data/notice content is dropped, and
private/human approval flags in the original records are never rewritten.

The combined archives wrap already compressed inputs without a costly second
compression pass. Fixed outer headers make their bytes independent of runner
file timestamps and permissions. Every nested file hash and expected member is
verified; missing/extra/duplicate members, links, traversal paths, altered bytes
and files reaching the 2 GiB upload limit stop publication. The source archive is
close to that limit with current inputs; future growth may require a separately
reviewed packaging change rather than omitting source content.

The original **v0.1.0** release remains at its 17-file layout. Legacy verification
and its pinned recovery record remain supported. GitHub's two automatic repository
source downloads are additional links and do not replace dependency source delivery.
This change is prepared on `develop`; it takes effect after a future authorized
merge into protected `main`. It neither bumps the version nor rebuilds v0.1.0.

Local verification — **240 release-tool tests pass**, including six-file
publication rehearsals for pre-release and stable versions, unchanged legacy
recovery, complete nested input preservation, deterministic packaging, tampering,
unsafe/missing/duplicate members and upload-size rejection. Python lint/format,
document/workflow formatting and actionlint pass. Real candidate packaging runs
with the next version; the current installers do not need another local test.

Future packaging checklist:

- [x] Keep both installer bytes and all original source/data/notice/record inputs.
- [x] Publish one combined source archive and one combined notice archive.
- [x] Retain one checksum file and one public provenance file.
- [x] Verify nested input hashes, exact file sets, archive safety and upload size.
- [x] Preserve legacy v0.1.0 verification and the protected owner publication gate.
- [ ] Merge the focused change through protected main's required checks when authorized.
- [ ] Verify the next version's real six-file candidate before publication; no new
      installed-app test is requested for the unchanged current v0.1.0 release.

## Flow and permissions

1. **Plan** runs only on this repository's `main`, checks matching Tauri/npm/Cargo
   versions, default branch and the existing `macos-release` protection. A released
   version is skipped; an existing incomplete tag fails closed. `0.x.x` and
   `alpha.N`/`beta.N`/`rc.N` versions are pre-releases; `1.0.0` and later without
   suffixes are stable.
   Release titles use only the version: **YomiMado v0.1.0**.
2. **seed-inputs** runs automatically on protected `main`, without an environment
   approval or personal token. GitHub requires
   `contents: write` to read unpublished drafts, so this isolated job uses a
   short-lived job token and sends **GET requests only**. It checks current main,
   effective main rules, publisher environment protection, unique private seed identity and declared/actual byte
   hashes. It exports three pinned macOS seed files and the pinned Windows
   dictionary snapshot into separate one-day artifacts. It creates no release or
   tag and approves no installer. No personal token or new secret is needed.
3. **Build macOS Apple Silicon** retains the reviewed frozen runtime, 74 dependency
   archives, source comparison, ad-hoc sealing, mounted verification and offline
   smoke. **Build Windows 11 x64 CPU installer** runs the existing short-build CPU
   ONNX recipe and complete installed terms/UI/runtime/source checks. It never
   builds Torch from source. Both builders have **read-only** repository permission,
   receive no private-input credential and verify transferred input hashes. Windows
   downloads no daily replacement dictionary and does not stage a draft release.
4. **verify-transfer** requires both successful builders. It verifies their exact
   file sets, hashes, source commit, version and classification, then creates
   `verified-desktop-candidate` with the six-file layout above. Original sources,
   dictionaries, notices, component input records and per-platform checksums are
   preserved inside the archives. `desktop-SHA256SUMS.txt` covers the public
   delivery, and provenance binds every retained platform input.
   Diagnostic `windows-main-evidence` is separate from published assets. Detector
   weights and test screenshots never enter the delivery.
5. **publish** waits for a new review in `macos-release` after the combined artifact
   exists. The owner must test **both exact new installers** first. It verifies
   all six public files and their retained inputs, protection, current main,
   classification and absent tag,
   creates one `v<version>` at that commit and uploads one private draft. Every
   uploaded asset's GitHub SHA-256 and state must match before publication; main
   is checked again after the upload. A failed platform/check or an advanced main
   prevents publication. Tags and existing assets are never overwritten.
   Publisher-only concurrency keeps tag creation/uploads serial without holding
   later builds behind a pending human review. Uploads are never cancelled by a
   later main push. Main now includes this follow-up through PR #3.

The environment keeps its historical `macos-release` name to preserve its already
configured reviewer, exact `main` branch rule and disabled administrator bypass.
Its **publish** review now covers both platforms. Builds and private input transfer
require no manual review. The agent never supplies the owner publication review.
Build/provenance files retain `installedAppVerified=false`
and private Windows flags: automated checks do not rewrite archived bytes or
pretend to have performed the separate human test.

## First execution and remaining external steps

- [x] Protect exact branch `main` with active ruleset
      [Protected main](https://github.com/chonnakanch/yomimado/settings/rules/24885215):
      pull requests, resolved comments, GitHub Actions `gates` and current-base
      checks; deletion and force pushes blocked; bypass list empty. Required PR
      review count is zero for this solo-maintainer project. The separate installer
      publication approval remains required.
- [x] Remove build approval; check effective main rules before private inputs and
      publication. Gate checks run on every main PR and develop/main push without
      path filters, so a documentation-only PR can satisfy the required check.
- [x] Historical private setup `756b7dc6…`: automated suite and hash-confirmed
      local six-check report pass on Windows 11 x64. New main setups need fresh
      exact-hash local reports.
- [x] Shared workflow, strict transfer/upload gates, permissions and version rules
      implemented; existing macOS runtime scope preserved.
- [x] Owner explicitly authorizes PR #1's first versioned merge to `main`; both
      required checks pass and the merge starts the automatic release run.
- [x] Both hosted builders and combined verification pass at current main
      `5159473` in run `38201230907`; protected publication is waiting for the owner.
- [x] Verify all seven downloaded Mac files and confirm the exact DMG's
      existing-Mac installed gate with the maintainer; fresh-Mac waiver retained.
- [x] Maintainer confirms the exact Windows setup hash and all six local checks
      pass on the confirmed Windows 11 x64 PC; untested hardware cases retained.
- [x] Hosted transfer verifies all 17 exact files and source/version/hash bindings.
      Independent agent inspection of the Windows/combined ZIP is not performed
      locally; protected publication rechecks files and uploaded asset digests.
- [x] Owner approves the original **publish** after both new exact-installer tests pass.
      Keep fresh-Mac testing waived and Windows AMD, additional/mixed-scale/left-of-
      primary monitors and a clean machine missing WebView2 explicitly untested.
- [x] Separately authorize and merge focused PR #4 at `a30d0ba`; dispatch
      pinned recovery `38257468295` on protected main without rebuilding.
- [x] Recovery `38257468295` passes the automatic exact-candidate gate in 6m 10s.
- [x] Owner supplies the new protected recovery review; its publisher verifies
      the unique uploaded draft by ID and publishes it successfully.
- [x] Public release contains both installers and all 17 uploaded source/notice/
      checksum/provenance assets; public API identity/digests and downloaded
      combined record/checksum bytes verify against the tested candidate.

Any upload failure leaves the draft private. A created partial tag/draft requires
owner investigation before an intentional rerun or version change; the workflow
does not delete history or silently repair public artifacts. If a reviewed seed
disappears or changes, restore its exact original assets privately; do not publish
it or widen builder permissions. Changed shared OCR/dependency/licence inputs
still require a newly reviewed macOS seed instead of using stale runtime code.

Local verification — 2026-10-11: **222 release-tool tests pass**, including actual
publisher-shell rehearsals for `0.1.0`, `1.0.0-beta.1` and `1.0.0`. Unsafe
default branch, stale/advanced main, missing effective main rules, unprotected environment, tag collision and
tampered upload cannot publish. Workflow actionlint, Python lint/format and
document formatting pass. The macOS seed comparison is preserved. The separate
**Checks** workflow runs these lightweight publisher and
version tests on every `main` PR and `develop`/`main` push with read-only permission and local fake APIs; it
neither builds an installer nor accesses private seeds.

Hosted gate-check record — [run `38155209350`](https://github.com/chonnakanch/yomimado/actions/runs/38155209350)
passes on `develop` at `cbeddb5e3e0a66d02e786eaf2251b3b9f3012574` in **15 seconds**.
It executes the publisher/transfer rejection tests and macOS version/source/artifact
tests using local fake APIs. It does not claim the protected main input transfer,
macOS/Windows combined builds or final human publication gate have executed.
