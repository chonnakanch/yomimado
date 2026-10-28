# Shared desktop release checklist

v0.7.0 preparation — **2026-10-28**: branch `release/0.7.0` binds version/runtime
source `2059ccbbc16dcd8a102eba00ae71b8dcee92a42f`, based on merged PR #45.
All 477 frontend, 310 service/contracts, 98 local macOS native and 166 release-tool
tests pass, with formatting/lint, TypeScript, native/frontend builds and workflow
syntax checks. The `194dd57` seed is incompatible with changed runtime inputs.
A private replacement candidate passes mounted bundle/platform/signature,
offline smoke and all 30 frozen-module/entrypoint source comparisons. Its unsigned
source/licence delivery awaits owner review; no new seed is activated. Main merge,
exact CI installer acceptance and protected publication remain unapproved. See the
[preparation record](release-preparation-0.7.0.md).

v0.6.0 observed public pre-release — **2026-10-28**: GitHub reports
[v0.6.0](https://github.com/chonnakanch/yomimado/releases/tag/v0.6.0) published on
2026-10-22 at `e1d75bd4e8aab9d659bf22f089070dd2a1328f3e`, with nine uploaded assets.
The public tag resolves to that exact commit. Reported installer SHA-256:

- macOS: `4261e4c9f880f5db9053e7eebdb1d5a051fa791db2823bb1059242afbd08fc71`
- Windows: `2e7b2771aea6d4a7735f6273d36c14624f22c12351b8829fd434003032daed03`

These are observed hosted metadata, adding no new local installer/hardware test,
acceptance or waiver. The earlier preparation state below remains historical.

v0.6.0 preparation — **2026-10-22**: branch `release/0.6.0` binds version source
`194dd5704b2a07c5f57c380f60adac35c748e46d`. Application and release-tool checks
pass, including all six hosted Checks at `9f3d290`. The owner approved the exact
replacement source/licence delivery and private seed activation. The
[new seed](macos-runtime-seed.md#v060-replacement-seed--2026-10-22) passes mounted
source/platform/signature and offline service smoke checks. Main integration
and exact CI installer acceptance/publication remain pending. See the
[preparation record](release-preparation-0.6.0.md); prior approvals and installer
hashes retain their original scope.

v0.5.0 public pre-release — **2026-10-21**:
[Recovery run `39587407949`](https://github.com/chonnakanch/yomimado/actions/runs/39587407949)
completed successfully after the workflow repair merged at
`6fa6a4d497d0deb92b7255907e41826bef0f60b4`.
[The public release](https://github.com/chonnakanch/yomimado/releases/tag/v0.5.0)
retains original installer source `8ff3be2621096a9804cc23ba33902f5aab34da55`,
nine uploaded files and the original PR-based notes. Published installer SHA-256:

- macOS: `778c865a7b95cc05becdfc6526aa492f0cf6bf41fb72841bc9bc7218e51df1f7`
- Windows: `aa69306dfab65cadf21702e2e6ad537faf725c03af36693a7e58f4be05e6e8c6`

The [recovery record](release-recovery-0.5.0.md#completed-recovery-and-retirement)
retains pinned artifacts and the successful outcome. The temporary workflow is
retired at the owner's request. These are observed hosted publication metadata;
this record adds no new local installer acceptance, hardware test or waiver.

v0.5.0 publication blocked — **2026-10-21**: after PR #27 merged at
`8ff3be2621096a9804cc23ba33902f5aab34da55`,
[Release `39571798373`](https://github.com/chonnakanch/yomimado/actions/runs/39571798373)
passes plan, private inputs, both installer builds and combined verification.
The publisher is rejected before running any step because deployment ref
`refs/pull/27/merge` does not match the protected environment's main-only rule.
An owner rerun has the same rejection. No tag or asset upload is performed by
these blocked publisher jobs. The [v0.5.0 recovery record](release-recovery-0.5.0.md)
binds the retained nine files, notes, original source and artifact digests.
Exact-installer acceptance and a fresh protected publication review remain separate.

0.4.0 public release metadata and retained disclosure — **2026-10-20**:
[v0.4.0](https://github.com/chonnakanch/yomimado/releases/tag/v0.4.0) identifies
source `bfdcbf2e313af824155cde6d3b08e27c0d5d2825` and nine uploaded files, plus
GitHub's two automatic repository-source downloads. The public asset list reports
macOS DMG SHA-256
`785d80f97a10978b0cde56e8c4cbf38c1828245e8121ac7e15e74900fb50c066`
and Windows setup SHA-256
`601b4458299a6fe93b16c0dbda72dea9b5bab4794af497ed8f1d8277d1c1f684`.
These are observed hosted metadata, without new local installer tests.

The owner requests public notes with only PR titles/numbers and Full Changelog.
The previous publisher's acceptance/limitations statement is retained here:

> Both exact CI installers were confirmed by the maintainer through the protected
> release environment. Fresh-macOS testing remains waived. Windows AMD,
> mixed-monitor/left-of-primary layouts and missing-WebView2 hardware cases remain
> untested.

Complete source-only rebuilding remains unverified. Sources, notices, checksums
and provenance remain downloadable assets. Moving this disclosure out of the
public description adds no acceptance, waiver, installer or publication approval.
Historical preparation/failure evidence follows unchanged.

0.4.0 macOS packaging repair — **2026-10-20**:
[Release `39378092468`](https://github.com/chonnakanch/yomimado/actions/runs/39378092468)
at `097cf7d6805e7530231dc918e3828d6502afbd56` passes planning, seed transfer,
source preparation and macOS DMG build/verification. The macOS job fails after
**11m 7s** during `Assemble only release files and bind their digests`:
`verify-artifact` rejects the candidate because the reused optional ZIP is named
`YomiMado_0.3.0_translation_torch.zip` instead of the current release's 0.4.0 name.
The repair changes only the verified output copy's filename. Its bytes, hash,
embedded descriptor (including the original 0.3.0 download URL), member/model
identity, size and source notices are preserved. The original public component
remains the descriptor's download source; the new release carries identical ZIP
bytes under its own versioned asset name. The strict artifact-name/hash checks
remain enforced, and ONNX cannot be relabelled as the macOS Torch component.

The Windows builder passes in **44m 59s**, reporting setup SHA-256
`140cc02bef0b7e30b75ee3629206b1bf0305b5861539ecadecf52590edde16cf`.
This is hosted evidence, without new local exact-installer acceptance. Combined
verification and publication are skipped; no verified joint candidate exists.
The macOS output is not uploaded after its packaging gate fails.

Local repair verification: 148 release-tool tests, script lint/format, document
formatting, pinned actionlint and runtime reuse pass. A synthetic installer/source
packaging rehearsal uses the actual retained Torch ZIP, preserving its
306,394,404 bytes and SHA-256
`e1c6a0ae58777d1eb4e8085eddff7a908fe0035e95c82178707178b7690434ef`.
The current-version output, sidecar and candidate record pass the strict
verifier. No installer was rebuilt for this local repair. A future authorized
repair merge must start a fresh Release; old run retries retain the old code.
Seed pins, installer acceptance and publication approval remain unchanged.

0.4.0 reuse/Checks repair — **2026-10-20**: after the owner's PR #17 merge at
`ce2a3df`, [Release `39371691358`](https://github.com/chonnakanch/yomimado/actions/runs/39371691358)
failed in `plan` at the known reuse rejection; both installer builders and
publication were skipped. A [technical repair](macos-runtime-reuse-0.4.0.md)
accepts only the exact frontend JLPT source/data/notice hashes, delivers their
separate terms and provenance, and adds real seed compatibility to required
Checks. Frozen runtime/seed pins and original approvals remain unchanged. Repair
integration and a fresh Release remain separate; retrying the old run uses its
old guard. Historical preparation evidence follows.

0.4.0 preparation — **2026-10-20**: version and release notes are prepared from
`develop`; local application/release checks pass. The existing macOS seed input
hashes verify, but committed-source reuse rejects the new JLPT source/data/notices
and changelog. **Main integration is blocked** until that review boundary is
resolved. See [the preparation record](release-preparation-0.4.0.md). No 0.4.0
installer, main merge, release dispatch, tag or publication approval is claimed.
Historical 0.3.0 evidence follows unchanged.

0.3.0 rebuild started — **2026-10-19**: the owner authorized the packaging fix's
main integration and a fresh release build. [PR #16](https://github.com/chonnakanch/yomimado/pull/16)
merged after all 12 push/PR checks passed, at
`e434b6cea96853079919e8acbbbd1468cc5c8bf4`. Fresh
[Release `39225156409`](https://github.com/chonnakanch/yomimado/actions/runs/39225156409)
and [exact-main Checks](https://github.com/chonnakanch/yomimado/actions/runs/39225156215)
have started from that commit. Their final outcomes and exact candidate hashes
are not yet recorded. Keep main at this source while it builds; installer
acceptance and protected publication remain separate and unapproved.

0.3.0 verification packaging repair — **2026-10-19**:
[Release `39193821074`](https://github.com/chonnakanch/yomimado/actions/runs/39193821074)
at `b4c95116dcc4c3abb1cdd732700336162155c994` passes the macOS builder in
**11 minutes 31 seconds** and the Windows builder in **44 minutes 31 seconds**.
`verify-transfer` then rejects the combined source archive at the existing
2 GiB upload limit. Publication is skipped; neither installer build failed.

The source repair uses `platform-sources-optional-translation-v1` for this
optional-component delivery, with **nine uploaded files**. The single source
archive becomes `YomiMado_<version>_sources_macos.tar.gz` and
`YomiMado_<version>_sources_windows.tar.gz`; the installers, combined notices,
checksums, provenance and two optional translation ZIPs remain. Both source
archives are required for the complete delivery. Original platform source/data
archives, paths and hashes are preserved byte for byte, and all prior member,
provenance, checksum and size guards remain. Seven-file `platform-sources-v1`
supports builds without optional components. Historical 6-, 8- and 17-file
layouts remain verifiable without rewriting their bytes.

This repair was initially prepared on `develop` only. Rerunning the old failed
job uses its old script and cannot apply the change; the subsequently authorized
main integration and new source-bound run are recorded above. No source/runtime
approval, installer acceptance or publication approval is inferred from the
packaging repair.

0.3.0 preparation — **2026-10-18**: the owner requests the version bump,
protected-main merge and release build. Version fields now agree on `0.3.0`,
with release notes for the resource reduction and user-selected local models.
The old macOS seed is incompatible; prepare and review its replacement without
weakening reuse/source guards. Windows acceptance will use the new real installer
build. Previous private candidate hashes do not establish acceptance of the new
0.3.0 installers. Protected publication remains a separate exact-candidate review.

Private resource-reduction verification — **2026-10-18**: macOS candidate
`907636e` passes mounted/platform/signature, copied frozen-service learning,
absent-translation OCR, explicit Marian import/restart and fresh native startup/UI
checks. The DMG is 625.63 MiB; all six variants of one owner-selected manga
screenshot preserve complete baseline responses. See the
[exact candidate evidence and limits](resource-reduction-acceptance.md).
The current UI offers user-installed translation through import or Ollama; the
older built-in download flow below describes retained historical tooling. Native
Windows installer checks, new runtime/source review, exact live capture/installed
acceptance and explicit publication approval remain separate. No release or
replacement CI seed was published, approved or activated.

Resource reduction source update — **2026-10-18**: future builds from the
Lindera/resource-reduction branch exclude OCR's UniDic/Fugashi resources and
make local translation an explicit optional download. See the
[implementation and checks](optional-translation-and-ocr-size.md). The new
`combined-optional-translation-v1` layout contains **eight uploaded files**:
the six historical files plus `YomiMado_<version>_translation_torch.zip` and
`YomiMado_<version>_translation_onnx.zip`. Platform and combined candidates and
checksums bind both archives; original six-file and legacy validation is retained.

Publish both exact component filenames alongside the matching new installers
before their embedded download descriptors can work. Each archive carries the
model card and Apache-2.0 terms. Exact-candidate smoke verifies absent-model OCR,
verified offline component installation, translation and persistence. Native
Windows, installer acceptance, refreshed source/notices/macOS runtime seed and
explicit publication approval remain required. No installer/component was
published or approved by this source update. Records below remain historical.

0.2.2 build follow-up — **2026-10-17**: [PR #12](https://github.com/chonnakanch/yomimado/pull/12)
merged at `32b5117cc93a934ff6adcbd41de0efa868cc3f33` after all 12 required/source
checks passed. [Exact-main Checks](https://github.com/chonnakanch/yomimado/actions/runs/38996949735)
also pass. [Release `38996949671`](https://github.com/chonnakanch/yomimado/actions/runs/38996949671)
passes planning, private-input verification and the macOS installer in 15 minutes
26 seconds, but Windows fails after 27 minutes 24 seconds while collecting three
original vcpkg port files: the unauthenticated Git blob API returned HTTP 403
rate-limit exceeded. No Windows installer/installed checks, combined candidate
or publisher passed in that run.

The focused repair downloads those same files from original vcpkg commit
`c6ba8a18a1513f0697a83cf88bd5e21300fc3fff` through raw URLs. All three bytes/hashes
match the already reviewed port inputs; original Git blob URLs remain as
provenance. Cached data is rechecked and changed downloads still fail closed.
No credentials, runtime/dependency/model versions or source omissions change.

The superseded macOS candidate is retained as historical build evidence:
`YomiMado_0.2.2_aarch64.dmg` SHA-256
`62826255d92a21947f950989081fb4164173ba1eb669ccfa4197bfa8f9892003`, in
[artifact `12088281223`](https://github.com/chonnakanch/yomimado/actions/runs/38996949671/artifacts/12088281223).
Its ZIP SHA-256 is `b444658555e4ca49365532fcf9c232edbdc5677a0526880e3207bcb86b63e892`.
This installer is not the repaired future candidate and has no owner acceptance
record. New main source will rebuild both installers with new hashes.

0.2.2 release preparation — **2026-10-17**: the owner requested release of the
system tray work as `0.2.2`. All five app version files agree. This candidate
includes native tray/menu bar controls, the Windows Common Controls test-manifest
repair and automatic Windows taskbar exclusion. Runtime/dependency/model/data
versions are unchanged. The tray feature's resolved Rust packages, sources and
notices match the approved seed; the reuse preflight permits that feature alone
and the explicitly reviewed native tray files. Shared OCR code, other dependency
or lock changes and unrelated build inputs still require seed review.

The owner request authorizes release preparation and protected-main integration.
Exact new installers and their checksums do not yet exist; source/debug passes
and previous installer reports do not supply their installed acceptance. Preserve
the separate protected publication review and all historical evidence below.
Public v0.2.1 is now available at `31f51a7`; its earlier waiting status below is
historical. No tag or installer from that release is replaced by 0.2.2 preparation.

Source follow-up — **2026-10-17**: the owner subsequently reported Windows
automatic page detection including the taskbar. The `develop` follow-up excludes
the monitor's reported taskbar work-area inset before automatic capture. It is
not included in the `31f51a7` candidate below. Preserve that candidate's exact
hashes and owner report; any rebuilt installer needs its own verification.

Verified 0.2.1 candidate — **2026-10-17**: [PR #11](https://github.com/chonnakanch/yomimado/pull/11)
merged the overlay startup repair at `31f51a7c4fe1bb192c3eeecea1f90d57d3ee5882`.
All exact-main [Checks](https://github.com/chonnakanch/yomimado/actions/runs/38930206019)
and [Release build/verification jobs](https://github.com/chonnakanch/yomimado/actions/runs/38930205981)
pass. macOS finishes in **12 minutes 24 seconds**, Windows in **46 minutes 45 seconds**,
and combined verification in **1 minute 50 seconds**. The Windows exact-setup
terms/rejection, startup/Quit, model setup/buttons/shortcuts and frozen
learning/persistence gates pass. The protected publisher is **waiting** in
`desktop-release`. The owner confirmed the Windows capture/keyboard check below;
0.2.1 publication still requires separate approval.

Download the [verified desktop candidate](https://github.com/chonnakanch/yomimado/actions/runs/38930205981/artifacts/12060264675),
artifact `12060264675` (**4,361,552,015 bytes**), retained until
**2026-10-31 00:03 Bangkok time**. GitHub artifact ZIP SHA-256:
`53fc5bef3e7a354973575eb16d43929a3f150374bacb49590794874df40d1a0b`.
Its six-file layout, exact source/version/classification, platform provenance and
member hashes pass the hosted gate. Member hashes are in
`desktop-SHA256SUMS.txt` and `desktop-release-candidate.json`; the large ZIP was
not downloaded locally. Metadata and local checks are retained under ignored
`services/ocr/build/release-0.2.1-31f51a7/`.

For the immediate Windows check, the smaller [Windows candidate](https://github.com/chonnakanch/yomimado/actions/runs/38930205981/artifacts/12060463340)
contains `YomiMado_0.2.1_x64-setup.exe`, `SHA256SUMS.txt`, platform sources/notices
and provenance. It is **2,456,862,457 bytes**, retained until
**2026-10-18 00:01 Bangkok time**, with artifact ZIP SHA-256
`3b033fe51ef55af54f331c765a0b7708c8e24475e6b2fadc7617ed1dfb047447`.
These are the same Windows files consumed by combined verification.

Exact installer hashes read from the successful `verify-transfer` job summary:

- `YomiMado_0.2.1_x64-setup.exe`:
  `b0aecb9d8d43d8ad30bf8350c56ae77fc3c17939a9aba1ab40e637c309d31933`.
- `YomiMado_0.2.1_aarch64.dmg`:
  `5643b7fa1ee3a1fd9169bc1c8e0ed89a1931ae15b2c5f2347de41d5ab58124c8`.

Combined source, notice and provenance hashes are retained in the local metadata
record and the downloadable checksums. Reading the summary does not constitute
an independent local installer hash/download or an installed-app visual test.

On **2026-10-17**, the owner answered **“Both modes and keyboard work”** to the
exact-candidate check: quit 0.2.0, install the linked 0.2.1 setup, then test Whole
Screen first on a fresh launch, Selected Area, and Read with keyboard → Enter.
This records visible outlines and popup activation working on the owner's Windows
setup for the installer hash above. It does not establish mixed-DPI coverage or
other untested hardware cases. Local macOS development launch
succeeded, but computer-use could not attach to the unbundled app, so it supplies
no visual pass. Exact macOS installer acceptance remains separate. Preserve the
existing fresh-Mac waiver, hardware limitations and source-only-rebuild/advisory
disclosures. Main must stay at `31f51a7` while this candidate awaits review.

0.2.1 preparation — **2026-10-16**: investigate the owner-reported Windows 0.2.0
scan completion without outlines in either capture mode. Read with keyboard reports
that no interactive result is available. Native source repair removes the new
WebView2 URL race, publishes OCR state before window creation and navigates reused
overlays from the already loaded selector page. Two new native regression cases
cover app origins/capture-query replacement and rejection of blank navigation bases.
The candidate uses matching app version `0.2.1` with no dependency/model changes.
Native tests, strict Clippy, formatting and debug compilation passed for the repair;
Windows visual verification and the new exact-installer acceptance remain open.
The published v0.2.0 tag/assets are retained; no 0.2.1 publication is approved.

Verified 0.2.0 candidate — **2026-10-16**: all checks pass for final main
`c03ee1edba4e0f545cb7ed85a7552c544a4bfcdc`, after
[PR #9](https://github.com/chonnakanch/yomimado/pull/9) completed native control-pattern
coverage. [Release 38892964547](https://github.com/chonnakanch/yomimado/actions/runs/38892964547)
passes planning, private input verification, both installer builds and combined
verification. macOS finishes in **11 minutes 28 seconds**, Windows in **46 minutes**,
and combined verification in **1 minute 33 seconds**. The Windows exact-setup
startup/Quit, model setup, buttons/shortcuts, cancellation, frozen learning and
persistence gates all pass. Protected `publish` subsequently passed; see the publication update below.
Superseded `820a352` retry `38889738880` was cancelled.

Download [verified-desktop-candidate](https://github.com/chonnakanch/yomimado/actions/runs/38892964547/artifacts/12045450534),
artifact `12045450534` (**4,361,498,912 bytes**), retained until
**2026-10-30 19:07 Bangkok time**. GitHub's artifact ZIP SHA-256:
`faf1a1521e46613dae765052f7882307a77085ee26a01d1e164ef4ba8e27f1d8`.
The hosted gate verifies the six-file layout, source/version/classification,
both platform records, installer/source/notice hashes and original input coverage.
Exact member hashes are in `desktop-SHA256SUMS.txt` and
`desktop-release-candidate.json` inside the artifact. The large ZIP and its members
were not independently downloaded locally. Public API job/step and artifact
metadata are retained under ignored `services/ocr/build/release-0.2.0-c03ee1e/`.

Publication update — **2026-10-16 19:22 Bangkok time**: the owner approved the
protected publisher and [v0.2.0](https://github.com/chonnakanch/yomimado/releases/tag/v0.2.0)
is public as a pre-release at `c03ee1e`. No separate detailed local installed-app
test report is recorded here; the protected review remains the publication evidence. Fresh-Mac and
Windows hardware limitations, dependency advisories and the unverified complete
source-only rebuild remain disclosed. Historical v0.1.0 evidence is unchanged.
The published tag and assets remain bound to `c03ee1e`.

Version 0.2.0 preparation — **2026-10-16**: the owner authorized the version bump,
protected-main merge and installer build. [PR #7](https://github.com/chonnakanch/yomimado/pull/7)
merged at `645ba088118f41880abfc37df1b595fa85e3ad42` after all required
[Checks 38840926023](https://github.com/chonnakanch/yomimado/actions/runs/38840926023)
passed. All five version files agree on `0.2.0`, with no dependency changes.
The refreshed [macOS source/runtime seed](macos-runtime-review-0.2.0.md) has explicit
source/licence-only approval and exact uploaded-hash verification. Release
[38841492110](https://github.com/chonnakanch/yomimado/actions/runs/38841492110)
built from the merged main commit. All main
[Checks 38841491986](https://github.com/chonnakanch/yomimado/actions/runs/38841491986)
pass. The macOS installer job passes in **10 minutes 50 seconds**; Windows
packaging produced a setup, but the installed-startup gate failed because the UI
driver required Invoke on the toolbar's ExpandCollapse menu button. Later Windows
tests, combined verification and publication were skipped. A focused driver repair
adds pattern-aware menu opening and a synthetic ExpandCollapse-only regression
fixture; ordinary Invoke actions remain covered. The Windows-only helper is
explicitly scoped outside the unchanged macOS frozen runtime. No new exact-installer
acceptance or publication approval is recorded. Historical v0.1.0 evidence below
remains unchanged.

The driver repair [PR #8](https://github.com/chonnakanch/yomimado/pull/8) passed
all push and pull-request checks, including the ExpandCollapse-only Windows
fixture, and merged at `820a352f5d75216706f0ea35e9622e29a15a7e4c`.
The corrected [Release 38889738880](https://github.com/chonnakanch/yomimado/actions/runs/38889738880)
passed planning and built a fresh macOS candidate before cancellation. The earlier run's installer
hashes are superseded; no acceptance is carried forward. Corrected main
[Checks 38889739313](https://github.com/chonnakanch/yomimado/actions/runs/38889739313)
pass on the exact merge commit.

Follow-up inspection found the same assumption in scan actions: `aria-pressed`
buttons expose Toggle instead of Invoke. The driver now supports both patterns,
with a real WPF Toggle-only fixture exercised from both pressed states. The
ExpandCollapse menu and ordinary Invoke paths remain covered. This affects only
the Windows smoke driver; app, runtime and dependency inputs are unchanged.

Latest publication — **2026-10-13**: [PR #6](https://github.com/chonnakanch/yomimado/pull/6)
is merged at `b188b05dd42ac5553cfbc0c1188c9646e2ce29ca` after all 12 PR checks pass.
[Checks `38378686824`](https://github.com/chonnakanch/yomimado/actions/runs/38378686824)
and [Release `38378686892`](https://github.com/chonnakanch/yomimado/actions/runs/38378686892)
succeed on main. Planning, private input transfer, both installer builds, combined
verification and the protected publisher all succeed. [YomiMado v0.1.0](https://github.com/chonnakanch/yomimado/releases/tag/v0.1.0)
is public again, as a **pre-release**, at the new source commit.

The release now contains the six-file layout below. Independent public API checks
confirm the exact tag/source target, title/classification and all six uploaded
asset names, states, sizes and SHA-256 digests. Downloaded public provenance and
checksum bytes also verify and bind both platform records to this commit.
The large installers and nested archives were not independently downloaded locally;
their byte/content gates passed in Actions and were rechecked by the publisher.

| Current published installer | SHA-256                                                            |
| --------------------------- | ------------------------------------------------------------------ |
| Windows x64 setup           | `61bbd7aefa46d895c1afae9d549e0d357d364bc647341d32ef08fe0957f74b59` |
| macOS Apple Silicon DMG     | `1d6cadbff7e454d09c790bc002b259ea0f8a2997392e6034bda8f9cb698df462` |

These installer bytes differ from the October 12 delivery. No new exact-hash local
acceptance report has been received in this chat; previous human passes remain
bound to their original hashes. Publication success does not supply that test
evidence, and archived `installedAppVerified=false` flags remain unchanged.
Existing hardware waivers and dependency-advisory/source-only-rebuild limitations
remain disclosed. The owner is satisfied with v0.1.0; no additional test request
is made here.

Availability update — 2026-10-13: the owner removed `v0.1.0`; its public release
and downloads were temporarily unavailable before the new publication above. The publication and acceptance
records below are historical evidence. The authorized cleanup merge does not
restore a tag or publish a replacement. Release planning now rejects stale runtime
reuse before seed downloads/builds when there is no published tag to skip.

Runtime refresh — 2026-10-13: the [new private macOS seed](macos-runtime-seed.md)
contains the service fixes from merged source `42edd4e`, with exact mounted
runtime/source verification and explicit source-only owner approval. New pins
are activated on `develop` after verifying all three uploaded macOS hashes.
The private Windows dictionary draft is restored with unchanged dictionary bytes
and a verified new outer-archive hash. Both input pin sets are integrated through
protected main in PR #6 and pass the hosted transfer/build gates. Dependency
advisory triage and local acceptance for the new exact hashes remain separate records.

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
The completed recovery's original procedure remains in Git at `2885586`.
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
[retired from the current documentation](README.md). Two routine
definitions remain: **Release** (`release.yml`) and **Checks** (`checks.yml`).
The required main status context remains `gates`. Packaging scripts and historical
source/licence/test evidence are preserved. Retirement is prepared on `develop`
for a future authorized main merge; no release assets or run history are deleted.

The October 13 consolidation uses **six uploaded files** (historical; future
optional-component builds add the two ZIPs described above):

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
and files reaching the 2 GiB upload limit stop publication. The single source
archive reached that limit in the 0.3.0 build; the platform split recorded above
replaces it for future candidates without omitting source content. Each new
source archive must still remain below the same limit.

The original October 12 **v0.1.0** delivery had the 17-file layout; the October 13
republication uses six uploaded files. Legacy verification
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
- [x] Merge the focused change through protected main's required checks.
- [x] Verify the real six-file candidate in Release `38378686892` before publication.
      Local acceptance for the new installer hashes is not recorded; no additional
      current-release test is requested under the owner's direction.

## Prepare each new release before merging main

Follow the [release steps](release-runbook.md#release-a-new-app-version).
Complete this checklist before the protected main PR is merged:

- [ ] Update the five app version files and commit the intended version/code
      changes so the notes generator reads the new version at the selected commit.
- [ ] Preview PR-based notes from the actual previous published app tag to the
      exact target source, using Python 3.11+ and authenticated GitHub CLI:

      ```sh
      rtk python3 scripts/release_notes.py github \
        --previous-tag v0.3.0 \
        --revision v0.4.0 \
        --output services/ocr/build/release-notes/0.4.0-pr-preview.json
      ```

      Replace the example tag/source/path. For a new release, use its committed
      source rather than a precreated tag. Review titles, reverts and the final
      diff; direct commits have no individual PR entry. The publisher generates
      the list automatically. Public notes contain only the PR list and Full
      Changelog. Keep installation/model setup and source/licence guidance in README;
      retain verification evidence and limitations here and in release metadata.
      See [generation details](release-runbook.md#generate-and-review-release-notes).

- [ ] Run version preflight and review whether the intended runtime changes need a
      [replacement seed](release-runbook.md#build-a-replacement-macos-seed).
      Seed availability does not block ordinary PR Checks; Release strictly
      resolves a compatible reviewed seed before input downloads or builds.
      If the intended source changes during preparation, generate a fresh draft
      and reconcile any changed behavior before merging.
- [ ] Push the focused changes and require passing Checks for the main PR before
      authorized merge of `release/<version>` into main. Release starts
      automatically and waits for successful `gates` on that exact main commit.
      Routine feature/fix merges do not build installers; manual main dispatch
      remains available for recovery. Follow the jobs below, test the exact
      installers and obtain the separate protected publication approval.

GitHub generates a PR-list preview in `release-notes-preview` before publication
approval. The publisher checks its SHA-256 and source/version and puts Full
Changelog last. Verification records, asset hashes and provenance remain separate
from the public note body.

## Flow and permissions

1. **Plan** runs when a same-repository `release/*` PR merges into `main`, or on
   an explicit manual main dispatch for recovery. It rejects closed unmerged PRs,
   other head branches, forks and a mismatched merge SHA. It waits up to 15 minutes
   for successful GitHub Actions `gates` for the exact selected main commit,
   then checks matching Tauri/npm/Cargo versions, default branch and the
   `desktop-release` protection. A released
   version with its tag is skipped; an existing incomplete tag fails closed.
   For an absent tag, the subsequent input job resolves a compatible reviewed
   seed before large downloads/builds; changed shared runtime/dependency inputs
   require a newly reviewed seed.
   `0.x.x` and
   `alpha.N`/`beta.N`/`rc.N` versions are pre-releases; `1.0.0` and later without
   suffixes are stable.
   Release titles use only the version: **YomiMado v0.1.0**.
2. **seed-inputs** follows a successful Release plan on protected `main`,
   without a separate input-transfer approval or personal token. GitHub requires
   `contents: write` to read unpublished drafts, so this isolated job uses a
   short-lived job token. Private-input transfer sends **GET requests only**; the
   same job also calls GitHub's **POST content-generation endpoint** for PR notes,
   without creating a tag or release. It uploads the source-bound
   `release-notes-preview` and passes its SHA-256 to the protected publisher.
   It checks current main,
   effective main rules, publisher environment protection, unique private seed identity and declared/actual byte
   hashes. [Dynamic seed selection](release-runbook.md#dynamic-reviewed-seed-selection)
   binds one owner-approved compatible macOS seed to this run. It exports its four
   files and the pinned Windows dictionary snapshot into separate one-day artifacts,
   plus the SHA-bound selection record for 14 days. It creates no release or
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
5. **publish** waits for a new review in `desktop-release` after the combined artifact
   exists. The owner must test **both exact new installers** first. It verifies
   all six public files and their retained inputs, protection, current main,
   classification and absent tag,
   checks the saved PR-note preview hash/source/version, creates one
   `v<version>` at that commit and uploads one private draft. Every
   uploaded asset's GitHub SHA-256 and state must match before publication; main
   is checked again after the upload. A failed platform/check or an advanced main
   prevents publication. Tags and existing assets are never overwritten.
   Publisher-only concurrency keeps tag creation/uploads serial without holding
   later builds behind a pending human review. Uploads are never cancelled by a
   later main push. Main now includes this follow-up through PR #3.

The shared publisher uses `desktop-release`, replacing the historical
`macos-release` name after the 0.2.0 publication. The replacement must preserve
required reviewer `chonnakanch`, the exact `main` branch rule and disabled
administrator bypass. Keep the old protected environment for historical runs;
changing workflow names does not rename their recorded environment. Its **publish**
review covers both platforms. Builds and private input transfer
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
      publication. Gate checks run on every main PR and main push without
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
