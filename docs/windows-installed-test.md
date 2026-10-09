# Windows candidate test record

Status — 2026-10-09: the replacement's complete automated installed-app suite
passes in [Windows run `37802965979`](https://github.com/chonnakanch/yomimado/actions/runs/37802965979)
at `c69eff996f7e85ea88ecb4f0407e05cf5d8ec8b5`. The maintainer reports successful
installation, detector import availability, OCR, shortcuts, dictionary lookup,
saving and viewing saved entries on the confirmed Windows 11 x64 PC. On
2026-10-09 the maintainer supplied the tested setup's PowerShell SHA-256;
it matches the current draft's checksum file and GitHub asset digest exactly.
The human installer gate remains **OPEN**, and source/native clearance is separate.

Current [owner-only candidate draft](https://github.com/chonnakanch/yomimado/releases/edit/untagged-a171bf97df5f42e7448e):
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

| Manual case                                                            | Reported result  | Limit                                                                                                                     |
| ---------------------------------------------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Setup and detector-import panel                                        | Pass reported    | Exact setup hash verified; import/cancel/wrong-file/relaunch cases need confirmation                                      |
| OCR and shortcuts                                                      | Pass reported    | Visual alignment recorded at three scales below; exact shortcut/scanning and scale-specific interaction cases remain open |
| Dictionary lookup, saving and viewing                                  | Pass reported    | Kanji, saved sentences and restart/reboot persistence not specifically confirmed                                          |
| OCR boundary precision                                                 | Observation open | Boxes are close to text, with uneven padding/clipped character edges; no clear global offset in supplied screenshots      |
| Browser/SmartScreen, console/cleanup, offline and uncached translation | Untested         | No specific PC result supplied                                                                                            |
| Upgrade/uninstall, WebView2 prerequisite cases and multiple monitors   | Untested         | No specific PC result supplied; mixed scaling and left-of-primary cases remain untested                                   |

Display evidence — 2026-10-09, for the verified setup above: Windows Settings
shows **2560 × 1440**, landscape, at **100%** scaling. The maintainer supplied
OCR screenshots labelled **100%**, **125%** and **150%** on that display.
At each scale, regions remain near the text across the page without an obvious
page-wide offset or accumulating drift. Record this as visual alignment evidence
at all three scales, with uneven detector boundaries still observed. Exact
selection-drag accuracy, click/hover targets, popup placement and relaunch after
each scale change are not specifically confirmed by these screenshots.

| Scale | Visual OCR alignment                         | Interaction/relaunch coverage |
| ----- | -------------------------------------------- | ----------------------------- |
| 100%  | Observed; Settings confirms scale/resolution | Pending specific result       |
| 125%  | Observed; scale reported by maintainer       | Pending specific result       |
| 150%  | Observed; scale reported by maintainer       | Pending specific result       |

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
   Attempt a second instance: it must show an occupied-port/startup error, not
   reuse another process. The bundled runtime must work without developer
   Python, Python PATH entries or CUDA. Record actual data folder
   `%APPDATA%\com.yomimado.desktop`; notices are in `<install>\ocr\notices`.
3. Before importing a model, verify the missing-model message. Cancel import,
   reject a wrong file, then import the original publisher's detector. Expected
   SHA-256: `1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f`.
   Relaunch and verify the imported model persists. The setup must not contain
   detector weights; importing copies your file into the writable data folder.
4. Use Ctrl+Shift+O on synthetic vertical and horizontal `学校へ` text. Check
   aligned regions, click/hover and popup placement. Verify 学校 reading/word
   meanings, 学 kanji meanings/readings and attribution. Request a new local
   sentence translation explicitly; a cached result alone is insufficient.
5. Try page scan, a saved scan area and Ctrl+Shift+S. Verify overlay visibility,
   focus, cancellation, and no leftover full-screen input-blocking selector.
6. Visual OCR alignment is recorded at 100%, 125% and 150% display scaling.
   Complete selection-drag accuracy, click/hover and popup-placement checks at each scale.
   Relaunch after changing scaling. If available test two monitors with different
   scaling, a monitor left of primary and layout changes. Otherwise mark those
   hardware cases untested; one 2K monitor does not cover them.
7. Disconnect internet after WebView2/model setup. Repeat capture, lookup and an
   **uncached** translation. Save a synthetic word/sentence; relaunch, verify
   those entries and cached translation. Reboot, then test shortcuts/capture.
8. Remove only test entries. Upgrade/reinstall using disposable test data and
   verify imported model and intended learning data survive. Uninstall and
   record whether data is retained; do not delete unrelated user data. Test
   offline setup with WebView2 already present. Report any case not exercised.

Public distribution remains blocked by the separate Windows native/source
review and this exact-installer confirmation. No macOS testing waiver transfers
to Windows. Joint publication must wait for both platforms' installer gates.
