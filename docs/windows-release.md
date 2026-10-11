# First Windows pre-release plan

Current private candidate — 2026-10-11: [run `38133593809`, attempt 2](https://github.com/chonnakanch/yomimado/actions/runs/38133593809)
at `8c46366d04e96d5356c250605e7ea936db209eb3` passes the complete
build/install/UI/OCR/learning/persistence and uploaded-asset suite in **45 minutes
42 seconds**. The [owner-only draft](https://github.com/chonnakanch/yomimado/releases/tag/untagged-369bebe25308d4e82cc2)
contains the verified setup, corresponding sources, dictionaries, notices and
provenance. `YomiMado_0.1.0_x64-setup.exe` SHA-256:
`7ff298c597de9c33d23bb598bf16d6f41761219e51fc0b61951ed6c54174c6d9`.

The maintainer confirms that exact downloaded hash and that the rightward
OCR-box offset is fixed at **100%, 125% and 150%** on the previously confirmed
Windows 11 x64 PC and 2560 × 1440 display. The maintainer also confirms all
listed browser/security, model/shortcut/cleanup, offline learning, restart/reboot
persistence and upgrade/uninstall/reinstall checks pass for this same setup.
The local installer checklist is complete; protected publication approval stays open.
See [the installed test record](windows-installed-test.md).

Downloaded diagnostic artifact `11701215883` matches GitHub SHA-256
`4b2267a29f12e16f8ad07d258542b4afb150e505ac1e1230b974bc78774fb6f8`.
Its setup/provenance bindings, installed startup/cleanup, model/buttons/shortcuts,
horizontal/vertical OCR, tokenization, dictionaries, kanji, uncached translation
and restart persistence verify. The exact embedded source-built NSIS plugin,
source-only WebView loader and canonical VC runtime checks pass. The service
contains 80 AMD64 PE inputs, CPU ONNX inference and no Torch/CUDA or bundled
detector weights. Hosted Windows Server results remain distinct from the PC report.

The downloaded source and notice bundles match SHA-256
`8a3d170f77e2c4f242890dab35e62e19c47c13d58e3ce6d6a94cf314b59cfea8` and
`003876ac910258ad006ab5281604ff5d854c16d255b33beaf686d719fcd314bb`.
Their native preferred archives, Python Rust crates/notices, ONNX inputs/ports,
NSIS and Sudachi originals/notices verify against the pinned records.
See [the delivered-source inspection](windows-source-review.md).

The earlier draft-creation HTTP 403 is resolved by an owner-prepared empty
exact-commit draft and an early read-only preflight; asset uploads then succeed
without broader permissions. The candidate sends no release-create,
release-update or tag-create API request. The public tag is verified absent.
The intermittent upstream NSIS spawn test is resolved in this run by executing
all tests sequentially, preserving source bytes, locked inputs and production
build flags. All 206 release-tool tests, Python/workflow lint and macOS
runtime-reuse scope checks pass locally; no test is skipped or failure retried
automatically. Previous failure evidence remains in Git at `02be7e0`.

Before a candidate run, save an empty draft in GitHub Releases with tag field
`windows-private-test-<full source SHA>`, exact target commit `<full source SHA>`,
pre-release selected, and a title/body clearly marking private testing and open
gates. Use **Save draft**, never Publish or create a Git tag. A newly pushed
commit may stop at this early preflight until its draft is ready; rerun that
unchanged job after preparation. Nonempty/published/ambiguous/wrong-target drafts
are rejected; existing assets are never overwritten or deleted automatically.

Previous private candidate — 2026-10-11: [run `38108583125`](https://github.com/chonnakanch/yomimado/actions/runs/38108583125)
at `ca0fed317976dcbf3267101324859e497f2b0487` succeeds in **46 minutes 8 seconds**.
Exact installation, hidden bundled-service startup without developer Python/CUDA,
quit cleanup, model setup/cancellation, buttons/shortcuts, horizontal/vertical OCR,
tokenization, dictionaries, kanji, uncached translation and restart persistence
all pass. The installed source-built NSIS plugin, source-only WebView loader and
unchanged canonical VC runtime copies pass their exact-input checks. The frozen
service contains 80 AMD64 PE inputs and uses CPU ONNX inference, without Torch,
CUDA or bundled detector weights. Hosted Windows Server execution does not
establish Windows 11 hardware coverage.

The [owner-only draft](https://github.com/chonnakanch/yomimado/releases/tag/untagged-a60c37d3e98452ad3180)
contains all eight verified assets. `YomiMado_0.1.0_x64-setup.exe` has SHA-256
`2a5ef545208214efabb9dc37bf88e15089c7a5ee69ca84ac58fb449afe063ce6`.
Downloaded diagnostic artifact `11692047068` matches GitHub SHA-256
`dfcfa3ba25054f555681b466357f25ba57a0a4fa59cce23992409542681fb3f7`.
The downloaded source archive matches SHA-256
`9dcd33c393830d84f9bd547f4080c463c262af8313b8c210bd6083f2d8d1622b`;
the notices archive matches
`bf5db559a02d6c652a7b37c60bdfd988d9ef1f8592f983e20c7cd866a7d701d4`.
Their detailed inspection is recorded in [the source review](windows-source-review.md).

The previous setup's maintainer-confirmed feature pass included a uniform
rightward OCR-box offset at all three scales. The Windows-only correction
disables the overlay shadow: pinned Tao adds hidden client-area insets for
undecorated shadowed windows, whereas OCR positioning assumes an inset-free
origin. The replacement's exact-hash visual retest above closes that defect.
Keep candidates private while distribution review and protected approval are open.
The maintainer now accepts the linked Community 2022 terms but confirms
they have **not obtained a copy** yet. The licensed-copy requirement and component-specific end-user terms
remain unresolved. A [notice draft](windows-microsoft-distribution-notice.draft.md)
is prepared for review, not activated in the installer. Full source-only rebuild
is not claimed. Public approval flags remain false; protected human approval
and joint release-on-main integration remain blocked. No public tag is created.

Historical trial runs and failed-runtime findings remain recoverable in Git at
`ee1b7f5`. This plan describes the active ONNX candidate only. The retired long
Torch source-build workflow, tools, manifests and exclusive tests are removed;
prebuilt Torch remains confined to export/parity preparation. Required sources,
full notices, replacement instructions and active build/verification recipes stay.

The table below describes the current ONNX replacement. Historical installed
and PC results above remain bound to their original setup hashes.

| Requested gate                | Current evidence                                                                                                  | Remaining work                                                                                                      |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| 1 — Pinned environment/freeze | Final CPython 3.11.17/NumPy 2.4.6/CPU ONNX freeze, parity and exact installed checks pass                         | Complete                                                                                                            |
| 2 — Native licences/sources   | 80 frozen AMD64 PE files; exact input/source bindings and downloaded source/notices hashes verify                 | Microsoft redistribution entitlement/end-user terms; final distribution review; full source-only rebuild unverified |
| 3 — Private installed app     | Exact NSIS install/startup/cleanup, UI/model/shortcut, embedded plugin, WebView/CRT and private asset checks pass | Local checklist complete; protected publication approval remains open                                               |
| 4 — Installed runtime         | Final installed geometry, tokenization, dictionary/kanji, fresh translation and restart persistence pass          | Hosted and listed PC checks complete                                                                                |
| 5 — Separate PC               | Windows 11 x64/hash confirmed; listed local checks and corrected alignment pass at 100%/125%/150%                 | AMD/mixed-monitor/left-of-primary/missing-WebView2 cases remain untested                                            |
| 6 — Joint release-on-main     | Existing macOS path preserved; no Windows publisher enabled                                                       | Integrate only after distribution and protected exact-installer human gates pass                                    |

The active candidate builds the minimal OpenCV runtime from pinned sources with
IPP, video and GPU backends disabled. Generated `/MD` compiler commands, native
imports, frozen detector probes and exact installed OCR pass. The standalone
OpenCV audit remains available for diagnosis; it is not another required installer
build. See [the native worksheet](windows-native-rebuild.md).

## Target and scope

Initial planned target: **Windows 11 x64**, Rust
`x86_64-pc-windows-msvc`, a downloadable **NSIS setup executable on GitHub
Releases**. Start with a per-user install. Defer MSI, Windows ARM64 and older
Windows support until separately tested. This is direct distribution outside
the Microsoft Store, with the existing capture → recognize → click → learn
features and CPU inference; no CUDA installation should be necessary.

Use the project's hobby distribution policy: paid signing is not a prerequisite
for the first candidate. Record whether the exact installer and executable are
unsigned or Authenticode-signed. Browser-downloaded unsigned applications may
show SmartScreen warnings; capture the actual result and document it. Do not
disable Defender or SmartScreen globally to obtain a passing test. If signing
is added later, keep credentials out of chat and git and verify the signature
and timestamp rather than silently publishing an unsigned replacement. See
[Tauri's Windows signing guidance](https://v2.tauri.app/distribute/sign/windows/).

Use WebView2's `downloadBootstrapper` mode initially, keeping the installer
smaller. Disclose that setup needs internet if a compatible WebView2 runtime
is missing. OCR/lookup/translation should operate offline after prerequisites
and the user-installed detector are available. Test the missing-runtime path;
do not assume every target PC already has it. See
[Tauri's installer and WebView2 options](https://v2.tauri.app/distribute/windows-installer/).

Detector ONNX weights remain **user-installed**, excluded from installers,
source delivery and public CI artifacts. Use only synthetic/private local test
images. No feature redesign or model-payload optimization in this work.

## Repository audit and first implementation slice

The existing cross-platform `xcap` capture abstraction, geometry transforms,
Ctrl+Shift+O / Ctrl+Shift+S shortcuts, overlay and Python API can be reused.
Windows functions have a hash-bound maintainer pass; the uniform
rightward overlay offset is resolved on the exact corrected setup in [the test record](windows-installed-test.md).

Concrete packaging gaps:

- Windows startup is now separate from the reviewed macOS path: it launches
  `runtime/yomimado-ocr.exe` without a console, supplies explicit resource/data
  paths, checks PID/instance readiness after the service binds loopback and
  closes a kill-on-close job when the desktop exits. Installed startup and normal
  quit cleanup pass in Windows CI; the exact-hash local checklist now passes,
  while protected publication approval remains open.
- `tauri.release.conf.json` targets DMG and contains macOS settings. The separate
  Windows release override supplies the production CSP and OCR resources.
- `requirements-macos-release.txt` and `build-macos-prerelease.sh` are specific
  to Apple Silicon: custom OpenCV, Accelerate NumPy, macOS native binaries and
  notices cannot be used as Windows runtime inputs.
- `windows-candidate.yml` builds only `develop`; its job can stage an owner-only
  draft but cannot approve the installer or publish a release. It prepares
  source-built Python, hash-pinned Windows wheels and
  CPU ONNX inference, freezes the service, builds per-user NSIS, installs it, checks
  startup/quit and frozen learning, and exports a test candidate with hashes.
  A later UI/learning failure retains an owner-only diagnostic candidate and
  records the failed/skipped outcomes; it never changes the failed job or grants
  installer/public-distribution approval.
  Native/source evidence remains unapproved. macOS clearance does not approve
  Windows inputs. The main publisher is unchanged; no public Windows path exists.

First slice: freeze the existing Python entry point as
`runtime/yomimado-ocr.exe` on Windows, bundle resources, and launch it from an
installed private desktop build without a developer Python installation.
[PyInstaller requires separate OS builds](https://pyinstaller.org/en/v6.16.0/usage.html#supporting-multiple-operating-systems);
the macOS frozen runtime is not a Windows seed.

## 1. Establish the Windows runtime

- [x] Confirm Windows 11 x64 test hardware and record its OS build, CPU and
      display layout/scaling. A Windows ARM PC under emulation is a separate case.
      Maintainer confirms a 64-bit OS/x64 processor, Windows 11 Home 25H2 build
      26200.9457, i5-14500 and a 2560 × 1440 display tested at 100%/125%/150%.
      This covers the reported single monitor; other hardware cases remain open.
- [x] Select and pin Windows Python, Node, MSVC/SDK, Rust, PyInstaller and hooks;
      preserve npm/Cargo locks and record exact versions and download hashes.
- [x] Create a Windows-specific Python lock, replacing macOS-only dependencies
      and recording CPU Torch/torchvision, tokenizer, image and ONNX compatibility.
      Avoid FFmpeg/video support, training binaries and unused codecs where practical.
- [x] Collect the actual EXE/DLL/PYD inventory and native provenance: final
      run `38133593809` records 80 frozen AMD64 PE files, desktop CRT inputs
      and the separate i686 NSIS host/plugin. The CPU ONNX replacement excludes
      the original runtime's Torch/MKL/IPP inputs; exact installed identities pass.
- [x] Preserve pinned preferred sources, build recipes, modifications, full
      notices and relinking/replacement instructions. Verify the actual downloaded
      source/notices archive hashes and retained dependency source/notice bytes.
      See the final [source review](windows-source-review.md). Independent full
      source-only rebuilding remains unverified; no blanket clearance is inferred.
- [ ] Complete public-distribution review, including the maintainer's applicable
      Microsoft redistribution grant and Microsoft-only end-user requirements.
- [x] Freeze the service in an isolated Windows environment using
      `windows_packaged_main.py`, initially as a directory bundle. Include pinned OCR,
      translation and dictionary assets; exclude the detector weights.
      Run `37582948931` produced the executable; native/source approval and
      human installed-app approval remain open. Complete installed-runtime
      and UI automation passes for the replacement in run `37802965979`.
- [x] Run frozen health, synthetic vertical/horizontal OCR geometry, Sudachi,
      JMdict, KANJIDIC2, uncached translation and saved/cache restart smoke checks
      outside the checkout with fresh temporary data and empty model caches.
      A separately obtained, hash-checked detector is temporary smoke input only.

Exit: a reviewed Windows runtime works without installed Python, developer
paths or automatically downloaded models. Document its notice/source inventory
before treating any installer as a public candidate.

## 2. Package and run a private installed app

- [x] Add Windows service startup in Rust with the `.exe` resource path,
      hidden child console, explicit local asset/data paths and existing offline
      model flags. Keep the API on loopback and preserve the macOS path.
- [x] Verify startup failures and occupied service port produce useful errors;
      quitting/relaunching does not leave an orphaned service or reuse an
      unrelated process. Final hosted startup/UI/cleanup checks pass; PC cases
      remain separate. Avoid logging captured screen contents.
- [x] Use Tauri's writable app data directory for models, SQLite and indexes;
      verify the actual installed path. Reconcile the Python fallback and
      README paths if needed; do not write mutable data into install resources.
      CI records `%APPDATA%\com.yomimado.desktop`, verifies bundled startup and
      normal quit cleanup, and passes saved-data/cache restart. The separate PC
      passes the listed clean-quit and restart/reboot persistence checks on the
      exact current hash; occupied-port error handling remains automated coverage.
- [x] Add the Windows release configuration and the smallest build entry point
      needed to assemble reviewed resources and an NSIS per-user installer.
      Fail on absent runtime, missing notices, mixed architecture or model leakage.
- [x] Run frontend/Rust/service tests on Windows and targeted lifecycle/path
      tests for changed code. Build with locked dependencies and record the
      clean source commit and installer SHA-256. Replacement run `37802965979`
      builds/installs `c69eff996f7e`; its owner-only draft retains `SHA256SUMS.txt`
      and provenance, with all uploaded asset digests verified by the workflow.
- [x] Inspect the installed file inventory and PE architectures; detect missing
      DLL dependencies and developer-only paths. Repeat frozen smoke using the
      exact installed runtime and confirm source/notice manifest consistency.
      This attests to pinned manifest/file hashes and CPU/native loading,
      not approval of the still-open corresponding-source/licence review.

Exit: the private installer launches OCR/learning from the installed app under
a normal Windows user account, without a developer environment.

## 3. Maintainer tests on the separate Windows PC

Send the verified private candidate and hashes with a short numbered test
record. The maintainer performs these steps locally; live agent access is not
required. Record the exact hash, OS build and passed/failed/skipped result for
each case, with synthetic screenshots only if useful. New hashes need new
installer confirmation. A new user profile or disposable VM is useful for
first-run isolation; existing-machine results must be labelled accurately.

- [x] Browser download, exact hash match and installation with
      Defender/SmartScreen enabled; no terminal and clean quit. Maintainer
      reports pass for current setup `7ff298c5…`. Additional Start menu/error
      subcases are not inferred from this report.
- [ ] Missing WebView2 handling and documented prerequisite installation;
      test offline setup when the runtime is already present. Record any
      missing-runtime test that cannot be performed as untested.
- [x] Detector dialog cancellation, wrong-file rejection, hash-checked import,
      persistence after relaunch and clear missing-model messaging.
- [x] OCR, dictionary/kanji learning, new offline translation and both capture
      shortcuts pass in the maintainer's feature report and listed local checks.
      Horizontal/vertical geometry also passes hosted installed automation.
- [x] Page scan works in the maintainer's reported feature tests. Detailed
      focus/cancellation subcases remain hosted UI coverage rather than a new
      claim of individually reported PC results.
- [x] Corrected OCR-box alignment at 100%, 125% and 150% on the single
      2560 × 1440 display; matching popup and buttons respond. Exact current
      hash confirmed. Detailed hover/edge-target subcases are not inferred.
- [ ] Additional monitors/mixed scaling, left-of-primary layout and AMD
      hardware: untested. These limitations do not undo the recorded single-PC
      tests or claim coverage unavailable to the maintainer.
- [x] Offline capture/lookup/uncached translation; saved words/sentences and
      translation cache across relaunch, then shortcut/capture after reboot.
      The maintainer confirms saved data/model/cache after restart and reboot
      and the listed offline checks for the exact current setup.
- [x] Upgrade, uninstall and reinstall pass in the maintainer's listed tests.
      Do not infer a different uninstall retention policy; only disposable
      test data should be used when repeating these checks.

Exit: exact-installer confirmation, with failures resolved and limitations
explicit. macOS's fresh-Mac waiver does not imply Windows testing passed.

## 4. Add Windows to release-on-main automation

Only after the Windows candidate clears its runtime/source and installer gates:

- [ ] Add a Windows build/verification job with pinned actions/tools and private
      candidate artifacts. Keep publication permission in the protected publisher.
- [ ] Use the same app version rules: `0.x.x` and `alpha.N`/`beta.N`/`rc.N`
      versions are pre-releases; `1.0.0` and later without a suffix are stable.
- [ ] Extend source-input comparison deliberately for Windows-only recipes and
      assets. The current macOS seed allowlist rejects new packaging paths;
      do not broadly allow changed shared OCR code, locks or unreviewed inputs.
      Shared runtime changes still require the affected platform's seed review.
- [ ] Coordinate both platform builds under **one version tag and publisher**.
      Independent tag creators would collide, and the current macOS workflow
      skips already published versions. Introduce Windows with a new versioned
      merge, not by silently replacing assets on an older release.
- [ ] Verify both platform candidates, source/notices, hashes and provenance
      after artifact transfer. Gate publication on exact installed-app approval
      for both platforms; no partial release when a required platform fails.
- [ ] Upload setup EXE, Windows source/notices, checksums and provenance beside
      the macOS assets in one draft. Check GitHub's uploaded hashes, flags and
      tag commit before making it public. Never upload detector weights.
- [ ] Finalize Windows release notes with supported architecture/OS, unsigned
      status if applicable, WebView2 behavior, model import, source links,
      hashes, data paths and verified/untested display cases.

## Next action and current limitations

Next action: keep setup `7ff298c597de…` private, establish the
maintainer's Microsoft redistribution entitlement by obtaining the licensed
Community 2022 copy after their reported terms acceptance, and review the
[component-only text draft](windows-microsoft-component-terms.draft.txt) and
acceptance requirement using [the prepared review](windows-microsoft-distribution-notice.draft.md).
The corrected overlay and listed local checks already pass on the confirmed
Windows 11 x64 PC with its downloaded hash recorded. Protected human approval
and joint release integration wait for distribution clearance. Actual installed input/source
bindings and downloaded source/notices checks pass; independent full source-only
rebuilding is unverified and public approval flags remain false.
The selected compiler/SDK fail closed if absent
from the hosted image. Dictionary downloads also fail if the daily snapshot
moves; supply the pinned snapshot or deliberately rebuild with new hashes. Candidate CI may assist development before publication CI is enabled.
The pinned dictionary originals are restored from the verified private seed
archive; their bytes are rechecked and retained in each candidate's
`windows-dictionary-snapshots.tar.gz`. Changed daily upstream bytes are rejected,
not silently repinned. A later rebuild must use these originals or deliberately
review new snapshots and obtain a new exact-installer result.

The hosted Windows Server result does not establish Windows 11 hardware,
browser/SmartScreen, upgrade/uninstall or scaled-display approval. Retain the
hash-bound maintainer results and explicitly untested cases. Required source,
notice and redistribution conditions remain independent of functional passes.
