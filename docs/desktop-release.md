# Shared desktop release checklist

Latest rollout — 2026-10-12: the owner explicitly authorizes [PR #3](https://github.com/chonnakanch/yomimado/pull/3),
merged at `5159473da21c952f1a4dc87c457bba82edf5edde`. Both required PR checks
pass; the new main [gate run `38201230971`](https://github.com/chonnakanch/yomimado/actions/runs/38201230971)
passes. [Joint build `38201230907`](https://github.com/chonnakanch/yomimado/actions/runs/38201230907)
passes planning and automatic private input transfer; both platform builders
are running without approval. Publisher-only concurrency is now deployed, so the older
waiting review does not hold later builds. Main has advanced: candidate
`99b1312` is superseded and its publication job must not be approved. Fresh
artifact hashes, automatic build results and both exact-installer local tests
remain pending. The Windows PC is available later; keep candidates private and
leave the protected owner publication review open.

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

The existing [workflow file](../.github/workflows/macos-prerelease.yml) is now named
**Desktop release from main**. Keeping the file replaces the previous macOS-only
publisher rather than introducing a second tag creator. `Windows private
candidate` remains the separate development-only installer workflow.

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
   `verified-desktop-candidate` with both installers, sources, dictionaries,
   notices, component input records and provenance. `desktop-SHA256SUMS.txt`
   covers the combined delivery; per-platform records/checksums remain unchanged.
   Diagnostic `windows-main-evidence` is separate from published assets. Detector
   weights and test screenshots never enter the delivery.
5. **publish** waits for a new review in `macos-release` after the combined artifact
   exists. The owner must test **both exact new installers** first. It verifies
   all 17 combined files, protection, current main, classification and absent tag,
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
- [x] Both hosted builders and combined verification pass at `99b1312` in run
      `38196721752`; protected publication is waiting for the owner.
- [ ] Download `verified-desktop-candidate`, verify `desktop-SHA256SUMS.txt` and
      test the exact DMG using [the Mac checklist](macos-clean-mac-test.md) and the
      exact setup using [the six Windows checks](windows-installed-test.md).
- [ ] Owner approves **publish** only after both new exact-installer tests pass.
      Keep fresh-Mac testing waived and Windows AMD, additional/mixed-scale/left-of-
      primary monitors and a clean machine missing WebView2 explicitly untested.
- [ ] Check the resulting public release contains both installers and every source,
      notice and checksum asset with the intended classification and commit.

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
**Desktop release gate checks** workflow runs these lightweight publisher and
version tests on every `main` PR and `develop`/`main` push with read-only permission and local fake APIs; it
neither builds an installer nor accesses private seeds.

Hosted gate-check record — [run `38155209350`](https://github.com/chonnakanch/yomimado/actions/runs/38155209350)
passes on `develop` at `cbeddb5e3e0a66d02e786eaf2251b3b9f3012574` in **15 seconds**.
It executes the publisher/transfer rejection tests and macOS version/source/artifact
tests using local fake APIs. It does not claim the protected main input transfer,
macOS/Windows combined builds or final human publication gate have executed.
