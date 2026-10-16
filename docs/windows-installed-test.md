# Windows candidate test record

Current 0.2.1 automated candidate — **2026-10-17**:
[Release 38930205981](https://github.com/chonnakanch/yomimado/actions/runs/38930205981)
at `31f51a7c4fe1bb192c3eeecea1f90d57d3ee5882` passes Windows in **46 minutes 45 seconds**
and combined verification. Exact-setup terms/rejection, startup/Quit, staged-model
UI, scan buttons/shortcuts/cancellation, frozen learning and persistence all pass.
[Main source Checks](https://github.com/chonnakanch/yomimado/actions/runs/38930206019)
pass too. This candidate contains the repair for the owner-reported missing OCR
regions in 0.2.0; source tests do not prove that visual behavior on a physical PC.

The [Windows test candidate](https://github.com/chonnakanch/yomimado/actions/runs/38930205981/artifacts/12060463340)
contains the setup, `SHA256SUMS.txt` and platform records. Its files are inputs to
the [verified combined candidate](https://github.com/chonnakanch/yomimado/actions/runs/38930205981/artifacts/12060264675).
ZIP digests and expiry are in [the shared release record](desktop-release.md).
No installer/archive was downloaded on this macOS development host. On
**2026-10-17**, the owner answered **“Both modes and keyboard work”** to the check
request to quit 0.2.0, install this exact 0.2.1 setup, then test a fresh Whole Screen
scan before Selected Area, visible outlines, keyboard region entry and popup
activation. This is an owner-reported pass for the Windows missing-overlay repair.
Exact setup SHA-256 from the successful combined verification summary:
`b0aecb9d8d43d8ad30bf8350c56ae77fc3c17939a9aba1ab40e637c309d31933`.

**Both capture modes and keyboard/popup interaction pass by owner report**;
physical mixed-DPI and the other hardware
limitations remain open. Publication is waiting for separate owner approval in
`desktop-release`. Do not transfer old human reports to these new installer bytes.

Current 0.2.0 automated candidate — **2026-10-16**:
[Release 38892964547](https://github.com/chonnakanch/yomimado/actions/runs/38892964547)
at `c03ee1edba4e0f545cb7ed85a7552c544a4bfcdc` passes the Windows job in
**46 minutes** and combined verification. The exact setup passes component-terms
rejection, installed startup/explicit Quit and service cleanup, missing/staged model
states, file-dialog cancellation, Settings close retaining the toolbar, scan
buttons/shortcuts and cancellation, plus frozen offline
OCR/learning and persistence. The driver covers Invoke, ExpandCollapse and Toggle;
its real Windows regression fixture also passes in required Checks.

The [combined candidate](https://github.com/chonnakanch/yomimado/actions/runs/38892964547/artifacts/12045450534)
and its ZIP digest are recorded in [the shared release record](desktop-release.md).
Hosted gates verify the exact member hashes. The ZIP/EXE and nested archives were
not downloaded locally. **No new local Windows 11/hardware acceptance is recorded**;
physical mixed-DPI and the other untested cases remain open. The owner subsequently
approved the protected publisher; [v0.2.0](https://github.com/chonnakanch/yomimado/releases/tag/v0.2.0)
is public as a pre-release. Earlier v0.1.0 passes below remain bound to their
original installer hashes.

Latest automated release — **2026-10-13**: [run `38378686892`](https://github.com/chonnakanch/yomimado/actions/runs/38378686892)
at `b188b05dd42ac5553cfbc0c1188c9646e2ce29ca` passes the Windows build in
**47 minutes 2 seconds**, combined verification and protected publication.
The six-file [public pre-release](https://github.com/chonnakanch/yomimado/releases/tag/v0.1.0)
contains setup SHA-256
`61bbd7aefa46d895c1afae9d549e0d357d364bc647341d32ef08fe0957f74b59`.
GitHub's uploaded digest matches the independently downloaded public provenance
and checksum record. The installer ZIP/EXE and nested archives were not downloaded
locally by the agent; hosted installed-runtime/content checks passed.

**Local acceptance for this new hash is not recorded.** The confirmed Windows 11
x64 PC specification and earlier six-check passes below remain historical; they
do not establish acceptance for this setup. No additional test is requested under
the owner's current direction. Hardware limitations remain unchanged, and no
new pass or waiver is inferred from publication.

Published — 2026-10-12: [YomiMado v0.1.0](https://github.com/chonnakanch/yomimado/releases/tag/v0.1.0)
is public as a pre-release. Both exact-hash local installer gates pass. The owner
approves protected recovery `38257468295`; verification and publication succeed
without changing the tested `5159473` source, tag or installer bytes. Independent
public API checks verify all 17 uploaded asset hashes/states and classification;
publicly downloaded combined provenance/checksum bytes also verify. Retain the
existing platform waivers, untested hardware and source-only rebuild limitation.
The historical preparation/open-gate statements below describe earlier stages.

Historical verified main candidate — 2026-10-12: owner-authorized PR #3 merges at
`5159473da21c952f1a4dc87c457bba82edf5edde`.
[Joint run `38201230907`](https://github.com/chonnakanch/yomimado/actions/runs/38201230907)
passes the Windows build in **36 minutes 18 seconds**, with installed terms/model/UI/
shortcuts/native/source/OCR/learning/persistence checks. Exact setup SHA-256:
`a8275246dc07a30f84a2109530bd68c3c0cceeed2556ce27fb09681d3a404602`.
Latest local report — 2026-10-12: the maintainer reports **“six windows checks
pass”**, then explicitly confirms **“Yes, hash matches”** for `a8275246…`.
All six checklist groups are **maintainer-reported pass** for this exact setup:
browser/security/install; model handling, buttons/shortcuts and cleanup; offline
OCR/tokenization/dictionary/kanji/new translation and saving/viewing; model/data/
cache persistence after restart/reboot; 100%/125%/150% alignment/clicks; and
upgrade/uninstall/reinstall. The exact-installer local gate is complete; this is
not an independent live-PC test or protected publication approval. No detailed
uninstall data-retention outcome beyond the broad pass is inferred.

The previously confirmed PC is Windows 11 Home 25H2 build 26200.9457, x64
OS/x64 Intel Core i5-14500, 32 GB RAM and one 2560 × 1440 display. Use that
confirmed test context; no new hardware specification is inferred. AMD,
additional/mixed-scale monitors, left-of-primary layouts, missing-WebView2 clean
machines and unreported detailed hover/edge-target cases remain untested.
Both builders and combined verification pass. The private
[verified-desktop-candidate](https://github.com/chonnakanch/yomimado/actions/runs/38201230907/artifacts/11726850805)
is retained for 14 days. GitHub artifact ZIP SHA-256:
`a6eec1b72e614ba45d30e9fe0651bb079b6266df0db5a4871e55bc896a5be91a`.
GitHub summary/transfer verifies the full delivery, and the maintainer confirms
the downloaded setup hash. Independent agent inspection of the Windows/combined
ZIP has not been performed locally; Actions verifies the delivery and the
protected publisher rechecks all 17 exact files before upload/publication. The protected publisher is waiting and has not
executed. Keep the candidate private and do not approve the superseded
`99b1312` run. Prior passing reports remain bound to their older installer hashes.

Superseded shared main candidate — 2026-10-12: [run `38196721752`](https://github.com/chonnakanch/yomimado/actions/runs/38196721752)
at `99b13124424901f425a49de7ed87557eee6230a9` passes all automatic Windows
build/install/UI/OCR/learning/persistence/source checks in **39 minutes 17 seconds**.
Combined macOS/Windows verification also passes. The private
[verified-desktop-candidate](https://github.com/chonnakanch/yomimado/actions/runs/38196721752/artifacts/11724359701)
contains `YomiMado_0.1.0_x64-setup.exe` with SHA-256
`e57ef7e9282023afcff540af86c48d4fb1a97ca42f6ee8932495a534bdfaa8cd`.
Hosted checks and GitHub summary hashes are verified; local download verification
and the six Windows 11 checks below are **pending** for these new bytes.
The maintainer reports the PC is available later. Keep the candidate private;
previous exact-hash passes do not apply. Protected publication remains waiting.

Component-terms candidate — 2026-10-11: [run `38142782743`, attempt 4](https://github.com/chonnakanch/yomimado/actions/runs/38142782743)
passes all automated gates in **46 minutes 19 seconds** at source
`f8396ccd5e7352a62e526c68438cc7f3c9cedc60`. The
[private draft](https://github.com/chonnakanch/yomimado/releases/tag/untagged-5d4b6531f87bae7fb27f)
contains eight hash-verified assets. `YomiMado_0.1.0_x64-setup.exe` SHA-256:
`756b7dc6003af202e4df95e946edcbc7fe409c41cfd0d2fc3be4062f758b4a1b`.
Missing/wrong silent and passive assent exit with code 2 without installing;
interactive terms start unchecked with Next disabled, and cancelling writes no
app files. Exact installed acceptance, startup/cleanup, native inputs, model/UI,
OCR/learning and persistence pass. Downloaded evidence `11707076117` matches
GitHub SHA-256 `56c7ee2b03767960651ab54196df5f21365d99f88eff1bc9cc8c563d5e45e31a`.
These are hosted Windows Server results, separate from the maintainer's PC report.

Historical local report — 2026-10-11: the maintainer confirms **“everything work”**
in response to this candidate's six-check handoff, then explicitly confirms
**“Yes, hash matches”** for `756b7dc6…`. Record all six checks below as
**maintainer-reported pass** for this exact setup, including the new terms page,
rejection/cancel, both shortcuts, offline learning, restart/reboot persistence,
100%/125%/150% alignment/clicking, and upgrade/uninstall/reinstall. This closes
its local checklist; it is not an independent live-PC test or protected
publication approval. No more detailed uninstall data-retention outcome is
inferred from the broad pass.

The previously confirmed hardware is Windows 11 Home 25H2 build 26200.9457,
x64 OS/x64 Core i5-14500, 32 GB RAM and one 2560 × 1440 monitor. AMD,
additional/mixed-scale monitors, left-of-primary layout and a clean machine
without WebView2 remain untested. Detailed hover/edge-target subcases are not
added by this broad pass. **Protected publication review remains open.**

A later `main` build creates different installer bytes and requires both its
macOS and Windows exact-installer tests before approving the publish job in
`desktop-release`. Builds and private seed transfer run automatically on protected
`main`; only publication requires the separate exact-installer approval.

Reusable six-check checklist — all six maintainer-reported pass for current
`a8275246…`. Historical `756b7dc6…` results remain bound to their own setup:

1. Browser download with Defender/SmartScreen enabled; terms initially unchecked;
   cancel before installation, then review/accept and install or upgrade normally.
2. No terminal; model import/cancel/wrong-file handling; both shortcuts and page
   scan; clean quit and relaunch without orphan processes.
3. Offline OCR, tokenization, dictionary/kanji lookup and a new uncached translation;
   save and view a word and sentence.
4. Imported model, saved entries and translation cache survive restart and reboot.
5. OCR alignment and clicking the matching region/popup at 100%, 125% and 150%.
6. Upgrade, uninstall and reinstall behave correctly; report retained or removed
   learning data explicitly. Keep previously untested hardware cases untested.

Previous verified exact candidate — 2026-10-11: [private draft](https://github.com/chonnakanch/yomimado/releases/tag/untagged-369bebe25308d4e82cc2),
from successful [run `38133593809`, attempt 2](https://github.com/chonnakanch/yomimado/actions/runs/38133593809)
at `8c46366d04e96d5356c250605e7ea936db209eb3`.
`YomiMado_0.1.0_x64-setup.exe` SHA-256:
`7ff298c597de9c33d23bb598bf16d6f41761219e51fc0b61951ed6c54174c6d9`.
All automated installed checks pass. The downloaded diagnostic artifact matches
GitHub SHA-256 `4b2267a29f12e16f8ad07d258542b4afb150e505ac1e1230b974bc78774fb6f8`;
its setup/provenance and embedded-plugin bindings verify.

The maintainer explicitly confirms that the tested download matches this hash,
the rightward OCR-box offset is solved at **100%, 125% and 150%**, and **all**
subsequently listed local installer checks pass. These are maintainer-reported
Windows 11 PC results, distinct from hosted Windows Server automation.

| Exact-installer local check                                                      | Maintainer result |
| -------------------------------------------------------------------------------- | ----------------- |
| Browser download with Defender/SmartScreen enabled and installation              | Pass              |
| No terminal, clean quit, model import/cancel/wrong-file handling, both shortcuts | Pass              |
| Offline OCR, dictionary lookup and new-sentence translation                      | Pass              |
| Saved data, imported model and translation cache after restart and reboot        | Pass              |
| Corrected OCR-box alignment at 100%, 125% and 150%                               | Pass              |
| Upgrade, uninstall and reinstall                                                 | Pass              |

The previously confirmed PC is Windows 11 Home 25H2 build 26200.9457, x64
OS/x64 Core i5-14500, 32 GB RAM and one 2560 × 1440 display. No new machine
specification is inferred. AMD hardware, additional monitors/mixed scaling,
left-of-primary layout and a clean machine without WebView2 remain untested.
The broad scale check does not add detailed hover/edge-target coverage.

**The local installer checklist is complete for this exact setup.** Protected
publication approval remains open. The owner now confirms downloading Community
2022 and accepting its terms. The component-terms acceptance implementation
changes the setup; hosted verification and the latest hash-bound local
installer report above now pass. Immutable private candidate metadata still has
`installedAppVerified=false` and `publicDistributionApproved=false`; this human
report does not rewrite archived bytes or approve the protected publisher.

The Windows-only correction at `1236d32` disables the OCR overlay's default
shadow. Pinned Tao 0.35.3 adds client-area insets for undecorated shadowed windows,
while OCR positioning assumes an inset-free origin. The replacement includes
that correction, and the exact-hash retest closes the observed offset without
a guessed pixel adjustment or a change to detector geometry/macOS behavior.
Local verification passes 10 frontend coordinate/overlay tests, nine native
overlay tests, Rust clippy/format and the frontend typecheck/production build.

The previous setup `2a5ef545208214efabb9dc37bf88e15089c7a5ee69ca84ac58fb449afe063ce6`
from run `38108583125` had a maintainer-confirmed feature pass but a uniform
rightward shift at all three scales. Its defect is superseded by the result
above; historical reports remain bound to their own hashes.

Runtime replacement — 2026-10-11: the Windows runtime selects
CPU ONNX inference, NumPy 2.4.6, a source-built Sudachi binding, unchanged
canonical VC runtime copies and a source-only WebView loader. Final packaging
also omits original export-only PyTorch weights. The exact-hash result above
covers this replacement. Earlier reports remain bound to their own setups.
Use the confirmed x64 PC specification unless the machine changes.

For any future rebuilt setup, the short report should contain its verified hash and
**pass / fail / untested** for these six checks:

1. Browser download, hash match, SmartScreen/Defender observations and per-user
   installation. Keep security protections enabled.
2. Launch/relaunch, no terminal, model import/cancel/wrong-file handling, both
   shortcuts and a page scan; quit leaves no app/service process.
3. OCR geometry, matching region click, word/readings/dictionary and kanji;
   translate a new sentence explicitly with the internet disconnected.
4. Save words/sentences, restart and reboot; confirm saved entries, imported
   model and translation cache persist.
5. At 100%, 125% and 150%, relaunch then check selection drag, OCR alignment,
   region clicks and fully on-screen popup controls on the 2560 × 1440 display.
6. Upgrade over the older private setup, then uninstall/reinstall; report shortcut
   removal and whether study/model data is retained. Mark additional monitors,
   AMD hardware and missing-WebView2 clean-machine cases untested if unavailable.

## Historical candidate results

These results describe older setups. Their instructions and open findings are
historical; the exact new setup and current local checklist status are above.

Private preparation candidate — 2026-10-10: [run `38022182370`](https://github.com/chonnakanch/yomimado/actions/runs/38022182370)
at `65ac794370fe2b0f60d7ed968ac0be2c04ca4d51` passes the complete automated
suite and private uploaded-asset checks. Its setup SHA-256 is
`4639a6351eb8ec708cc824fe96c98a0e1f82ccf304eb1e9641d19823a6d1782d`.
No manual result below applies to this rebuilt setup. Wait for the pending native
replacements before requesting another PC test; then use the numbered checklist
with the final candidate's exact hash. Source/native and human gates remain open.

Status — 2026-10-09: the replacement's complete automated installed-app suite
passes in [Windows run `37802965979`](https://github.com/chonnakanch/yomimado/actions/runs/37802965979)
at `c69eff996f7e85ea88ecb4f0407e05cf5d8ec8b5`. The maintainer reports successful
installation, detector import availability, OCR, shortcuts, dictionary lookup,
saving and viewing saved entries on the confirmed Windows 11 x64 PC. On
2026-10-09 the maintainer supplied the tested setup's PowerShell SHA-256;
it matches the current draft's checksum file and GitHub asset digest exactly.
The human installer gate remains **OPEN**, and source/native clearance is separate.

Maintainer-tested [owner-only candidate draft](https://github.com/chonnakanch/yomimado/releases/edit/untagged-a171bf97df5f42e7448e):
`YomiMado_0.1.0_x64-setup.exe`, matching `SHA256SUMS.txt` and
`windows-candidate.json`. All eight uploaded asset digests were verified by the
successful workflow. Do not use the repeated setup filename to identify a build;
compare the actual downloaded file hash with this draft's checksums before binding
manual results. No public version tag or release is created.

Verified setup SHA-256:
`51b0091103c10c03ecd3748039bd4db0631381fb43885fe7163b889821fba207`.
The owner-authenticated draft identifies this setup at the exact source commit
above. Its downloaded `SHA256SUMS.txt` is 667 bytes, SHA-256
`a6b4f0cb3f631d8dc8a3e3c0dd41ddf64276abbd2952adeb5aa35fee7440f9c0`,
matching GitHub's checksum-file digest; its setup entry matches both the
maintainer's report and GitHub's setup digest. The named manual results below
are now bound to this exact installer. This confirms build identity, not the
unreported checklist cases or full human installer approval.

The run's diagnostic artifact `windows-preparation-evidence` is 109,829 bytes,
SHA-256 `7da2a72053ce9522904b07f2100b9c7e7594545e173d8d5504cc48d3eac5119c`,
as recorded by GitHub's artifact API. This identifies the evidence ZIP, **not**
the setup EXE; its own checksum file must supply the installer hash.

| Manual case                                                                  | Reported result  | Limit                                                                                                                     |
| ---------------------------------------------------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Setup, detector-import panel and model retention                             | Pass reported    | Imported model remains after app relaunch; cancel/wrong-file cases remain unconfirmed                                     |
| OCR and shortcuts                                                            | Pass reported    | Visual alignment recorded at three scales below; exact shortcut/scanning and scale-specific interaction cases remain open |
| Dictionary lookup, saving and viewing                                        | Pass reported    | Saved words/sentences persist after app restart; kanji and saved-entry verification after reboot remain unconfirmed       |
| OCR boundary precision                                                       | Observation open | Boxes are close to text, with uneven padding/clipped character edges; no clear global offset in supplied screenshots      |
| Offline OCR, dictionary lookup and new-sentence translation                  | Pass reported    | Maintainer confirms internet-disconnected checks; translation-cache persistence remains unconfirmed                       |
| Quit cleanup, relaunch without console, shortcuts and page scan after reboot | Pass reported    | Both app/service processes disappear in Task Manager; occupied-port/second-instance case remains unconfirmed on this PC   |
| Browser/SmartScreen                                                          | Untested         | No specific PC result supplied                                                                                            |
| Upgrade/uninstall, WebView2 prerequisite cases and multiple monitors         | Untested         | No specific PC result supplied; mixed scaling and left-of-primary cases remain untested                                   |

Display evidence — 2026-10-09, for the verified setup above: Windows Settings
shows **2560 × 1440**, landscape, at **100%** scaling. The maintainer supplied
OCR screenshots labelled **100%**, **125%** and **150%** on that display.
At each scale, regions remain near the text across the page without an obvious
page-wide offset or accumulating drift. Record this as visual alignment evidence
at all three scales, with uneven detector boundaries still observed.

The maintainer then supplied three popup screenshots labelled 100%, 125% and
150% in response to the region-click check. Each shows the same selected region's
text in a fully on-screen popup. Record a scoped pass for opening the matching
popup from that region and keeping it on-screen at each scale. This tests one
region near the lower-right of the page; other targets/edges and hover behavior
are not specifically confirmed. On 2026-10-09 the maintainer additionally
confirmed that Analyze words, Save sentence, Translate locally and Close respond
at 100%, 125% and 150%, answering the explicit four-button check. Record button
responsiveness as a reported pass for this installer at each scale. This does
not by itself establish a fresh uncached translation or saved-sentence persistence after restart.
Selection-drag accuracy and relaunch after each scale change remain unconfirmed.

Offline/restart evidence — 2026-10-09: in response to the explicit instruction
to disconnect internet, translate a new sentence, restart the app and confirm
saved words/sentences remain, the maintainer confirms it works. Record reported
passes for offline uncached sentence translation and saved-word/sentence
persistence after app restart for the same verified installer.

Lifecycle/reboot evidence — 2026-10-09: the maintainer explicitly confirms all
four subsequent numbered checks pass on the same installer: after closing,
`yomimado.exe` and `yomimado-ocr.exe` disappear from Task Manager; relaunch opens
no terminal and retains the imported model and saved entries; OCR and dictionary
lookup work with internet disconnected; after reboot, both shortcuts and page
scan work. This resolves the named console/cleanup, model-retention, offline
capture/lookup and post-reboot shortcut/page-scan cases. It does not cover the
separate occupied-port, translation-cache persistence or saved-entry check after
reboot, nor approve the remaining installer checklist as a whole.

| Scale | Visual OCR alignment                         | Region click and popup placement | Popup buttons                 | Remaining coverage                           |
| ----- | -------------------------------------------- | -------------------------------- | ----------------------------- | -------------------------------------------- |
| 100%  | Observed; Settings confirms scale/resolution | Matching text; fully on-screen   | Respond; maintainer-confirmed | Selection, hover, other targets and relaunch |
| 125%  | Observed; scale reported by maintainer       | Matching text; fully on-screen   | Respond; maintainer-confirmed | Selection, hover, other targets and relaunch |
| 150%  | Observed; scale reported by maintainer       | Matching text; fully on-screen   | Respond; maintainer-confirmed | Selection, hover, other targets and relaunch |

The supplied manga and Settings screenshots remain user-local evidence and are not copied
into the repository or source delivery. They support visual capture/overlay/popup
operation and the visual scaling observations above, not every interaction or OCR result.
Personal account details visible in Settings are omitted from the test record.

Earlier candidate `79065df7ba34a3aaa4ddb3a1ebb30e164405742a`, run `37721943728`,
failed the human gate with a blank console, missing model setup, inactive scan
buttons and a shortcut freeze. Its setup hash was
`01a28c0f4964b2df1733814670b3024d8aa18c525b544965a50189ec25ecab0a`;
the [older draft](https://github.com/chonnakanch/yomimado/releases/tag/untagged-e4524b4cbafe468fe44d)
is diagnostic only and must not be approved. The replacement's UI/runtime fixes
and installed regression checks now pass; the earlier failure record is retained.
Never approve this record from automated CI alone. Each rebuilt setup needs its
own confirmation.

The candidate workflow stages an owner-only GitHub draft with `SHA256SUMS.txt`
and `windows-candidate.json` after exact installed startup/resource/native checks.
It retains a diagnostic setup even if later UI/learning checks fail; check the
run summary's individual outcomes before testing, and never approve failed or
skipped cases. It creates no tag and has no publication operation.
Installer/source archives are never uploaded as public Actions artifacts.
GitHub blocks Actions tokens from creating a draft targeting workflow changes
relative to main. Before staging, create an **empty draft** in the owner UI with
`windows-private-test-<full candidate SHA>` and the exact candidate commit as
target; save as draft, never publish/create a tag. The workflow can upload and
verify that empty draft. No credentials belong in git, logs or test reports.

Confirmed by the maintainer's System/About report (2026-10-08): **64-bit operating
system, x64-based processor**, Windows 11 Home **25H2**, OS build **26200.9457**,
Intel Core i5-14500 and 32 GB RAM. Previously reported: RTX 4070 Super and one
display, now confirmed at 2560 × 1440 with visual OCR evidence at 100%/125%/150%.
Device/product identifiers are intentionally omitted. The PC architecture is confirmed, while
the replacement has reported functional passes bound to the verified setup hash;
the prior candidate failed. Record scaling when reporting the remaining interaction cases.
GPU acceleration is not used; a CUDA installation is not required.

Fill in: candidate commit, setup filename/SHA-256, browser, System type,
Windows version/build, CPU, display resolution/scaling/layout, existing machine
or new profile/VM. For each step, report **pass / fail / untested** and brief
observations. Use only synthetic text/images and disposable study entries.

1. Browser-download the exact candidate. In PowerShell run
   `Get-FileHash .\YomiMado_0.1.0_x64-setup.exe -Algorithm SHA256` and compare with
   its checksum file. Record SmartScreen/Defender behavior and unsigned status.
   Install per-user and launch from Start. Do not disable security protections.
   Investigate damaged/malware warnings. Record WebView2 presence and test
   missing-runtime installation only in a disposable profile/VM if available;
   missing WebView2 needs internet with the bootstrapper configuration.
2. Quit/relaunch twice. Confirm no console flashes or leftover OCR process.
   Maintainer confirms both processes disappear after quit and relaunch opens no terminal.
   Attempt a second instance: it must show an occupied-port/startup error, not
   reuse another process. The bundled runtime must work without developer
   Python, Python PATH entries or CUDA. Record actual data folder
   `%APPDATA%\com.yomimado.desktop`; notices are in `<install>\ocr\notices`.
3. Before importing a model, verify the missing-model message. Cancel import,
   reject a wrong file, then import the original publisher's detector. Expected
   SHA-256: `1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f`.
   Relaunch and verify the imported model persists. The setup must not contain
   detector weights; importing copies your file into the writable data folder.
   Imported-model retention after relaunch is maintainer-confirmed; cancel/wrong-file
   handling remains unconfirmed on this PC.
4. Use Ctrl+Shift+O on synthetic vertical and horizontal `学校へ` text. Check
   aligned regions, click/hover and popup placement. Verify 学校 reading/word
   meanings, 学 kanji meanings/readings and attribution. Request a new local
   sentence translation explicitly; a cached result alone is insufficient.
5. Try page scan, a saved scan area and Ctrl+Shift+S. Verify overlay visibility,
   focus, cancellation, and no leftover full-screen input-blocking selector.
   Both shortcuts and page scan after Windows reboot are maintainer-confirmed;
   the detailed saved-area/focus/cancellation cases remain unconfirmed on this PC.
6. Visual OCR alignment, clicking the tested region and fully on-screen popup
   placement are recorded at 100%, 125% and 150% display scaling; the maintainer
   confirms all four popup buttons respond at each scale. Complete selection-drag
   accuracy, hover and additional targets/edges at each scale.
   Relaunch after changing scaling. If available test two monitors with different
   scaling, a monitor left of primary and layout changes. Otherwise mark those
   hardware cases untested; one 2K monitor does not cover them.
7. Disconnect internet after WebView2/model setup. Repeat capture, lookup and an
   **uncached** translation. Save a synthetic word/sentence; relaunch, verify
   those entries and cached translation. Reboot, then test shortcuts/capture.
   Offline new-sentence translation and saved-word/sentence persistence after app
   restart, offline OCR/lookup, and both shortcuts/page scan after Windows reboot
   are maintainer-confirmed. Cached-translation and saved-entry verification after
   reboot remain open.
8. Remove only test entries. Upgrade/reinstall using disposable test data and
   verify imported model and intended learning data survive. Uninstall and
   record whether data is retained; do not delete unrelated user data. Test
   offline setup with WebView2 already present. Report any case not exercised.

Public distribution remains blocked by the separate Windows native/source
review and this exact-installer confirmation. No macOS testing waiver transfers
to Windows. Joint publication must wait for both platforms' installer gates.
