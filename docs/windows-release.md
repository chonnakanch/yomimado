# First Windows pre-release plan

Status — 2026-10-07: independent Windows candidate preparation is implemented;
hosted build, actual native/source review and installed-app verification are
pending. See the [source worksheet](windows-source-review.md) and
[numbered PC checklist](windows-installed-test.md). The maintainer has a separate Windows 11 PC,
with no live agent access and no current physical access. Reported specs are
i5-14500, RTX 4070 Super, “25h” Windows and one 2K monitor; exact OS build,
System type and scaling remain unconfirmed. Build checks can run on a Windows GitHub Actions
runner; the maintainer will perform installed-app checks locally and report
results. Confirm the PC's architecture before claiming x64 coverage.

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
images. No feature redesign or model/installer size optimization in this work.

## Repository audit and first implementation slice

The existing cross-platform `xcap` capture abstraction, geometry transforms,
Ctrl+Shift+O / Ctrl+Shift+S shortcuts, overlay and Python API can be reused.
Windows capture, page scan and scaled-display alignment remain manually
unverified in [the implementation plan](implementation-plan.md).

Concrete packaging gaps:

- Windows startup is now separate from the reviewed macOS path: it launches
  `runtime/yomimado-ocr.exe` without a console, supplies explicit resource/data
  paths, checks PID/instance readiness after the service binds loopback and
  closes a kill-on-close job when the desktop exits. Windows CI verification
  remains pending; code completion does not clear the installed-app gate.
- `tauri.release.conf.json` targets DMG and contains macOS settings. Add a
  separate Windows release override with the production CSP and OCR resources.
- `requirements-macos-release.txt` and `build-macos-prerelease.sh` are specific
  to Apple Silicon: custom OpenCV, Accelerate NumPy, macOS native binaries and
  notices cannot be used as Windows runtime inputs.
- `windows-candidate.yml` builds only `develop`; its job can stage an owner-only
  draft but cannot approve the installer or publish a release. It prepares
  source-built Python, hash-pinned Windows wheels and
  CPU Torch, freezes the service, builds per-user NSIS, installs it, checks
  startup/quit and frozen learning, and exports a test candidate with hashes.
  Native/source evidence remains unapproved. macOS clearance does not approve
  Windows inputs. The main publisher is unchanged; no public Windows path exists.

First slice: freeze the existing Python entry point as
`runtime/yomimado-ocr.exe` on Windows, bundle resources, and launch it from an
installed private desktop build without a developer Python installation.
[PyInstaller requires separate OS builds](https://pyinstaller.org/en/v6.16.0/usage.html#supporting-multiple-operating-systems);
the macOS frozen runtime is not a Windows seed.

## 1. Establish the Windows runtime

- [ ] Confirm Windows 11 x64 test hardware and record its OS build, CPU and
      display layout/scaling. A Windows ARM PC under emulation is a separate case.
- [x] Select and pin Windows Python, Node, MSVC/SDK, Rust, PyInstaller and hooks;
      preserve npm/Cargo locks and record exact versions and download hashes.
- [x] Create a Windows-specific Python lock, replacing macOS-only dependencies
      and recording CPU Torch/torchvision, tokenizer, image and ONNX compatibility.
      Avoid FFmpeg/video support, training binaries and unused codecs where practical.
- [ ] Collect the Windows runtime's EXE, DLL and PYD inventory before clearing
      public distribution. Verify exact licences, notices and native provenance,
      including OpenCV, NumPy/BLAS, Torch/OpenMP, Pillow, GEOS and Python libraries.
      Select source builds or different binaries when concrete gaps require them.
- [ ] Preserve exact corresponding sources, build recipes, modifications and
      applicable relinking/replacement instructions for the actual bundled inputs.
      Verify archive hashes, source coverage and required notices; record review
      scope and any source-only rebuild limitations without claiming unrun checks.
- [x] Freeze the service in an isolated Windows environment using
      `windows_packaged_main.py`, initially as a directory bundle. Include pinned OCR,
      translation and dictionary assets; exclude the detector weights.
      Run `37582948931` produced the executable; native/source approval and
      installed runtime verification remain open.
- [ ] Run frozen health, synthetic vertical/horizontal OCR geometry, Sudachi,
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
- [ ] Verify startup failures and occupied service port produce useful errors;
      quitting/relaunching does not leave an orphaned service or reuse an
      unrelated process. Avoid logging captured screen contents.
- [ ] Use Tauri's writable app data directory for models, SQLite and indexes;
      verify the actual installed path. Reconcile the Python fallback and
      README paths if needed; do not write mutable data into install resources.
- [ ] Add the Windows release configuration and the smallest build entry point
      needed to assemble reviewed resources and an NSIS per-user installer.
      Fail on absent runtime, missing notices, mixed architecture or model leakage.
- [ ] Run frontend/Rust/service tests on Windows and targeted lifecycle/path
      tests for changed code. Build with locked dependencies and record the
      clean source commit and installer SHA-256.
- [ ] Inspect the installed file inventory and PE architectures; detect missing
      DLL dependencies and developer-only paths. Repeat frozen smoke using the
      exact installed runtime and confirm source/notice manifest consistency.

Exit: the private installer launches OCR/learning from the installed app under
a normal Windows user account, without a developer environment.

## 3. Maintainer tests on the separate Windows PC

Send the verified private candidate and hashes with a short numbered test
record. The maintainer performs these steps locally; live agent access is not
required. Record the exact hash, OS build and passed/failed/skipped result for
each case, with synthetic screenshots only if useful. New hashes need new
installer confirmation. A new user profile or disposable VM is useful for
first-run isolation; existing-machine results must be labelled accurately.

- [ ] Browser download, hash verification, SmartScreen result, per-user setup,
      Start menu launch, quit/relaunch and uninstall/reinstall or upgrade using
      disposable test data. Preserve unrelated user data and privacy settings.
- [ ] Missing WebView2 handling and documented prerequisite installation;
      test offline setup when the runtime is already present. Record any
      missing-runtime test that cannot be performed as untested.
- [ ] Detector dialog cancellation, wrong-file rejection, hash-checked import,
      persistence after relaunch and clear missing-model messaging.
- [ ] Ctrl+Shift+O selection and interactive vertical/horizontal OCR; popup
      hit-testing, dictionary/kanji attribution and uncached local translation.
- [ ] Page scan and Ctrl+Shift+S saved-area flow; overlay visibility, focus and
      cancellation without leaving a full-screen input-blocking window.
- [ ] Alignment at 100%, 125% and 150% scaling; two monitors with different
      scaling, one left of the primary monitor, plus layout changes where
      available. Specify missing hardware cases instead of claiming coverage.
- [ ] Offline capture/lookup/uncached translation; saved words/sentences and
      translation cache across relaunch, then shortcut/capture after reboot.
- [ ] Save/remove only synthetic test entries. Check upgrade/reinstall preserves
      intended learning data and the imported model; document uninstall retention.

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

Next action: execute the independent Windows candidate workflow from the
tracked `develop` commit, inspect the actual Windows inventory and resolve
source/notice gaps before public distribution. Download the exact test candidate
and use the numbered PC checklist when the hardware is available. The manifest
collects original sdists and source/binary archives; it does not claim complete
corresponding-source coverage. The selected compiler/SDK fail closed if absent
from the hosted image. Dictionary downloads also fail if the daily snapshot
moves; supply the pinned snapshot or deliberately rebuild with new hashes. Candidate CI may assist development before publication CI is enabled.
Hosted run `37582948931` built CPython 3.11.17, passed service/frontend and all
38 Windows Rust tests, and froze the OCR executable. Notice collection then
failed because Cargo UTF-8 metadata was read with the Windows default code page;
the scripts now specify UTF-8. Installer construction, native/source review and
installed-runtime checks remain pending.
No Windows runtime or installer is claimed to work yet. This macOS session
cannot validate Windows DLL loading, SmartScreen or physical display capture.
The maintainer's separate PC can supply the manual results once a candidate is
ready; coordinate file delivery and the checklist at that point.
