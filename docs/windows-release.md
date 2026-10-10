# First Windows pre-release plan

Latest automated candidate — 2026-10-10: [run `38022182370`](https://github.com/chonnakanch/yomimado/actions/runs/38022182370)
at `65ac794370fe2b0f60d7ed968ac0be2c04ca4d51` passes every build/install/UI/
OCR/learning/persistence and owner-only draft upload/hash step. Downloaded evidence
matches GitHub SHA-256
`b573952fce9a392da72f7a41b2fb3e106c5d58820909af614b4fd9b9891b6aa8`.
Exact setup SHA-256:
`4639a6351eb8ec708cc824fe96c98a0e1f82ccf304eb1e9641d19823a6d1782d`.
Its private draft identity is `windows-private-test-65ac794370fe2b0f60d7ed968ac0be2c04ca4d51`.
The new freezer record binds all three app-local VC DLLs to actual original
input paths/hashes; compiler/runtime terms and final source assembly remain open.
This candidate still uses the existing native runtime, not the separately audited
GEOS/OpenCV replacements or a completed source-built Torch. No PC retest is
requested yet, and no human result transfers from the `51b0091103c1…` setup.

Earlier automated candidate — 2026-10-10: [run `38019354851`](https://github.com/chonnakanch/yomimado/actions/runs/38019354851)
at `87731d65c50499a67ec7683e889402638ba557ca` passes the complete Windows
build/install/UI/OCR/learning/persistence suite and owner-only draft upload checks.
The downloaded evidence ZIP matches GitHub SHA-256
`38f3c13e714d2f704118b4705484d9749da37a9b59de5e7254a24d88517d3593`.
Provenance and installer-input records agree on setup SHA-256
`5db98f6b460d71367ff88f4f17c976ac62239b97fde56d92fe8f67c9dee31443`.
Find the private draft in [GitHub Releases](https://github.com/chonnakanch/yomimado/releases)
by identity `windows-private-test-87731d65c50499a67ec7683e889402638ba557ca`.
It includes the prepared notice supplement; native source clearance and both
approval flags remain open. The actual setup/source/notice archives have not been
downloaded for local inspection. No PC results are bound to this new setup, and
another PC test can wait until the native replacements are ready. The existing
maintainer results below remain bound to `51b0091103c1…`.

Status — 2026-10-09: [Windows run `37802965979`](https://github.com/chonnakanch/yomimado/actions/runs/37802965979)
passes all steps at `c69eff996f7e85ea88ecb4f0407e05cf5d8ec8b5`: pinned build,
per-user NSIS installation, resource/native/startup checks, missing-model setup,
import cancellation, occupied-port acknowledgement, scan buttons, both shortcuts,
selector cancellation and frozen OCR/learning/persistence. The owner-only draft
staging and uploaded-asset hash checks also pass. This is Windows Server 2022
execution, not a substitute for the separate Windows 11 PC tests.

The maintainer reports that the replacement installs, offers detector import,
and works for OCR, shortcuts, dictionary lookup, saving and viewing saved entries.
User-local screenshots show OCR regions close to the text across the page,
with uneven padding and some character edges outside the boxes. No clear global
position/scale error is apparent; detector boundary precision remains an observation
for follow-up, not a diagnosed coordinate bug or a passed scaling matrix.
The manga screenshots are not repository fixtures and are not included in delivery.
On 2026-10-09 the maintainer's PowerShell setup SHA-256 matches the owner-only
draft's checksum file and GitHub setup digest:
`51b0091103c10c03ecd3748039bd4db0631381fb43885fe7163b889821fba207`.
The named functional results are bound to this exact installer. Remaining PC
cases and approval of the full human installer gate are still pending.

The System/About report confirms **64-bit operating system, x64-based processor**,
Windows 11 Home **25H2**, build **26200.9457**, Core i5-14500 and 32 GB RAM.
Previously reported: RTX 4070 Super and one monitor. The 2026-10-09 Settings
screenshot confirms **2560 × 1440**, landscape, at **100%** scaling. OCR
screenshots labelled 100%, 125% and 150% show no obvious page-wide drift.
Visual alignment is recorded at all three scales. Subsequent popup screenshots
show the same selected region's matching text in a fully on-screen popup at each
scale: region clicking and placement pass for that tested target. The maintainer
also confirms Analyze words, Save sentence, Translate locally and Close respond
at all three scales. In a subsequent explicit offline/restart check the maintainer
confirms that a new sentence translates with internet disconnected and saved
words/sentences remain after app restart on the same verified installer.
The next four numbered checks also pass with maintainer confirmation: app/service
processes disappear after quit, relaunch opens no terminal and retains model/data,
offline OCR/dictionary lookup works, and both shortcuts plus page scan work after
Windows reboot.
Selection accuracy, hover, other targets/edges and relaunch after
each scale change still need specific results.
Browser/SmartScreen, occupied-port handling, translation-cache persistence,
saved-entry verification after reboot, upgrade/uninstall and the
remaining scaling interactions and multiple-monitor cases remain untested on that
PC unless separately reported. Screenshots stay user-local; personal account details
are omitted from the record.
Native licence/source clearance and human exact-installer approval remain open;
macOS packaging and the main publisher are unchanged. See the
[source worksheet](windows-source-review.md) and [numbered PC checklist](windows-installed-test.md).

Work independent of PC access progresses in **Windows GEOS source audit**:
run `37877467511` at `a10db77ec91d5e1e0f96f444b0a98376c641774a` passes a
pinned GEOS source build, upstream tests and DLL replacement in an isolated
frozen Shapely probe. Source/tool/notice pins and actual loaded-DLL checks pass;
the [native worksheet](windows-native-rebuild.md) records exact scope and
evidence identity. The current installer is unchanged. Full installed OCR
replacement is now prepared for execution against that exact private setup:
baseline/replacement OCR and learning smoke, actual DLL hashes and an exhaustive
installed-file comparison, with original DLL restoration. It remains unverified
until its hosted run passes. The first installed extension run cannot see the
private draft with its Actions token's read-only release listing. The protected
owner-input environment and maintainer approval passed in run `38016752910`.
Its subsequent draft lookup used the published-release tag endpoint incorrectly;
the corrected lookup uses the authenticated listing and retains safe preflight
diagnostics. Corrected run `38017337839` received approval. Its first attempt
stopped because the token was stored as a variable rather than a secret. Attempt 2
receives the secret but cannot see the matching private draft in the API listing.
The owner confirms the draft still exists and explicitly authorizes repository-only
Contents write access, with Workflows disabled, then updates the secret.
Attempt 3 passes private-input access, all 431 GEOS tests and isolated frozen
replacement, but fails the installed-service step before producing its OCR report.
Its downloaded evidence hash is verified. A definite verifier mismatch is fixed:
the historical setup must use its pinned original manifests instead of today's
changed source-input manifest. Phase diagnostics and tests preserve all exact
file/asset/architecture gates. A reviewed rerun is required; installed GEOS
replacement remains unverified. See the native worksheet for scope and hashes.
Reviewed rerun `38020734338` passes the exact original installed-service smoke,
then fails the audit's case-sensitive file-key comparison during DLL replacement.
Its downloaded evidence verifies and confirms exact original-file restoration.
Windows path keys are now normalized consistently with collision rejection;
a regression reproduces the mismatch without weakening content checks. The
corrected replacement still needs a new reviewed run; the tested setup is unchanged.
Corrected run `38021809403` now passes exact installed baseline/replacement OCR,
learning and persistence, actual replacement DLL loading, all 431 upstream tests,
5,400 unchanged installed files and exact original-file restoration. Its downloaded
evidence verifies independently. Packaging the replacement and final Windows
source/human approval remain separate; the downloadable installer is unchanged.
**Windows Torch source audit** also reaches native compilation, then fails on a
quoted include flag inside generated C++ build-option strings. The redundant flag
is removed and that source object is compiled early on rerun. Its downloaded
source/notice/cache/compiler evidence verifies; completed Torch/vision inference
and full installed replacement remain open. Neither experiment changes the
maintainer-tested setup.
The quoted-string correction passes real MSVC in rerun `38020734345`, which then
fails at the autograd engine's Unix-only `pthread_atfork` call. The build recipe
had replaced Windows default compiler flags and dropped `WIN32`. Extra flags
now initialize through the environment while preserving defaults; command checks
require Windows definitions and the early build includes the failing object.
The Windows flag correction passes real MSVC in run `38024770382`, but full
compilation fails after about 84 minutes on missing Kineto `ActivityType.h`.
Its downloaded evidence hash, preferred inputs, cache and compiler guards verify.
The recipe now pins the required original header source and full notices, checks
the failed object early, and emits progress every 30 seconds. The complete
Torch/vision build and probes still require a successful hosted rerun; this audit
does not build an installer or transfer approval to a new runtime.
Independent OpenCV run `37938195277` now passes its IPP-free source build,
DLL compiler-runtime linkage and native/frozen CPU detector probes, with its
downloaded textual evidence independently hash-verified. Full installed
recognition and final source coverage remain open.
Final source delivery and Intel-free Torch/OpenCV builds remain
separate work; the human gate is not approved by this audit.

Notice-supplement candidate run `38016673211` at
`902bcf6d3446fbeab65128cfa62ac93f5549a051` builds and installs its NSIS setup,
passes installed startup and frozen learning/persistence checks, and exports a
diagnostic candidate. Its installed UI regression and owner-only draft staging
steps fail. The downloaded evidence ZIP matches GitHub SHA-256
`74534086117b2628efafc2b676156638f48912640c8a5997990017b2f147f674`.
Its UI report passes missing-model setup, model-dialog cancellation, occupied-port
handling, manual selection, scan-area selection and the manual shortcut; it stops
at **page-scan button** without retaining the exception. The driver now saves the
failure message/type/line and visible-window responsiveness, minimization and
focus, while continuing to fail the job. The actual error from this run is needed
before changing application behavior or test expectations.
Local verification passes all 148 release-script tests, workflow lint,
documentation formatting, PowerShell 7.4.6 parsing and reviewed macOS seed reuse.
Windows PowerShell 5.1 executes this diagnostic successfully in run `38019354851`:
all five capture cases, cancellation, responsiveness, missing-model setup,
model-dialog cancellation and occupied-port acknowledgement pass. No app behavior
or test expectation was changed for this rerun; the earlier failure's cause is
not established. The newer run also passes private staging and uploaded hashes.
The exported provenance and installer-input record agree on setup SHA-256
`0129393b970cc4b5c55628b9fc308b3733e25daabe1b0d4cc8e61cfd861f2fe2`;
the setup bytes and source/notice archives have not been downloaded and private
staging is unverified. This failed run does not replace the maintainer-tested
setup or satisfy the installer gates. No human test is bound to this new hash.

Earlier candidate `79065df7ba34a3aaa4ddb3a1ebb30e164405742a` passed runtime
checks in run `37721943728`, but failed the human gate: a blank terminal,
absent detector panel, inactive scan buttons and a shortcut freeze. Its replacement
adds the Windows GUI subsystem, Windows model setup, asynchronous window commands
and a worker for shortcut window creation. Startup errors use a nonblocking dialog.
The complete hosted regression suite now passes in run `37802965979`.

Replacement run `37782181350` at `f5c157d6f9a4b0efdb39908e5054fbd061a37956`
built and installed NSIS, verified the x64 GUI executable/resources/startup,
and reached the missing-model panel and occupied-port dialog. Its UI harness
incorrectly required exit code 1 after acknowledgement; the pinned Tauri runtime
maps requested exits to its normal GUI exit path. The assertion now accepts
normal exit codes 0/1, records the actual code and retains responsiveness checks.
The remaining UI and learning steps were skipped in that run, so it produced no
download candidate and grants no installer approval. A complete rerun is required.

Run `37787583634` at `10b8aba894fe83d08fd7f02fb83771ad68413984` confirms
the model panel, disabled scanning without a model, occupied-port message,
acknowledgement with exit code 0 and the original app's responsiveness. Its next
UI case timed out after sending Escape to the just-created model file dialog.
The harness now waits for and invokes the enabled native Cancel control, waits
for frontend import completion, and waits for rendered selector instructions
before testing Escape. Remaining capture/learning checks still need a full run;
no failed-run installer was exported or approved.

Run `37794271949` at `80be890535305c2e3b349fc118561d850a0dfa02` again
built/installed NSIS and passed startup/resource/native checks. Its dialog test
could not find Cancel through UI Automation. Hash-verified diagnostics show the
actual `Open` dialog and a separate untitled auxiliary window; selecting the
first non-main window was unreliable. The harness now activates the named
dialog and clicks its enabled native `IDCANCEL` control, with frontend completion
and close assertions retained. It also records native child-control diagnostics
on failure. The replacement still needs a complete passing run.

Run `37798943690` at `7a8c4d82a9f10461c02ba7e94399c206bf9648a8` built
and installed the zlib setup. Its native Cancel control closed the dialog, but
the next frontend wait accessed a missing button while its label was temporarily
`Checking model…`. The wait now treats that as pending, with the same timeout
and enabled-button assertion. The workflow also runs frozen learning independently
of the UI driver and retains the exact startup-verified setup in an owner-only
draft for diagnosis even if later UI/learning checks fail. Any failed or skipped
case is recorded, the job stays failed, and both approval flags remain false.

Private verification builds now use NSIS zlib compression instead of LZMA:
compression dominated the failed reruns after a successful desktop compile.
This may increase the download size. The complete installed payload, native
inventory, checksums and GitHub asset-size limit are still verified; it grants
no source or installer approval. macOS packaging is unchanged.

The earlier [owner-only diagnostic draft](https://github.com/chonnakanch/yomimado/releases/tag/untagged-e4524b4cbafe468fe44d)
contains `YomiMado_0.1.0_x64-setup.exe` (893 MB), `SHA256SUMS.txt`, provenance,
notices, project/source preparation and the original dictionary snapshots.
All eight uploaded asset digests were checked against GitHub. The installed
desktop reports `NotSigned`; browser/SmartScreen behavior is still untested.

| Requested gate                | Current evidence                                                                                                                    | Remaining work                                                                                                                                   |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1 — Pinned environment/freeze | Passed in Windows Actions; CPython 3.11.17, pinned CPU wheels, frozen service                                                       | Native distribution review is tracked separately below                                                                                           |
| 2 — Native licences/sources   | Actual inputs, notices and preferred-source bindings collected                                                                      | Complete Windows vendor/terms review and corresponding-source delivery; resolve Intel MKL/IPP compatibility or run compatible replacement builds |
| 3 — Private installed app     | Exact NSIS installation and runtime checks pass; maintainer confirms quit cleanup, no terminal on relaunch and model/data retention | Remaining second-instance/occupied-port and installer cases                                                                                      |
| 4 — Installed runtime         | Geometry, tokenization, dictionaries, kanji, uncached translation, restart persistence, model exclusion and AMD64 payload pass      | Finish native source approval; x64 PC architecture and exact setup identity are confirmed, but remaining Windows 11 cases remain open            |
| 5 — Separate PC               | Model import, OCR, shortcuts, dictionary lookup and saved-entry viewing reported working for the verified setup hash                | Investigate boundary precision and complete remaining manual/scaling cases                                                                       |
| 6 — Joint release-on-main     | Existing macOS path preserved                                                                                                       | Deliberately gated on Windows source clearance and human exact-installer approval                                                                |

Independent IPP removal is prepared in **Windows OpenCV source audit**, with
original source/vendor notice pins, accepted CMake cache checks, synthetic
image/geometry and actual CPU detector inference in native/frozen probes.
Run `37934320710` passes these native/frozen checks. Locally hash-verified
evidence reveals the static CRT default remains enabled despite requested DLL
linkage; explicit disabling, generated `/MD` compiler-command checks and VC
runtime PE-import checks are added for a required rerun. It exports textual evidence only and leaves the
tested setup unchanged; full installed OCR replacement and Torch's MKL/OpenMP
replacement remain separate. See [the native worksheet](windows-native-rebuild.md).

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
Windows capture, page scan and scaled-display alignment remain manually
unverified in [the implementation plan](implementation-plan.md).

Concrete packaging gaps:

- Windows startup is now separate from the reviewed macOS path: it launches
  `runtime/yomimado-ocr.exe` without a console, supplies explicit resource/data
  paths, checks PID/instance readiness after the service binds loopback and
  closes a kill-on-close job when the desktop exits. Installed startup and normal
  quit cleanup pass in Windows CI; the human installed-app gate remains open.
- `tauri.release.conf.json` targets DMG and contains macOS settings. The separate
  Windows release override supplies the production CSP and OCR resources.
- `requirements-macos-release.txt` and `build-macos-prerelease.sh` are specific
  to Apple Silicon: custom OpenCV, Accelerate NumPy, macOS native binaries and
  notices cannot be used as Windows runtime inputs.
- `windows-candidate.yml` builds only `develop`; its job can stage an owner-only
  draft but cannot approve the installer or publish a release. It prepares
  source-built Python, hash-pinned Windows wheels and
  CPU Torch, freezes the service, builds per-user NSIS, installs it, checks
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
- [ ] Verify startup failures and occupied service port produce useful errors;
      quitting/relaunching does not leave an orphaned service or reuse an
      unrelated process. Avoid logging captured screen contents.
- [x] Use Tauri's writable app data directory for models, SQLite and indexes;
      verify the actual installed path. Reconcile the Python fallback and
      README paths if needed; do not write mutable data into install resources.
      CI records `%APPDATA%\com.yomimado.desktop`, verifies bundled startup and
      normal quit cleanup, and passes saved-data/cache restart. The separate PC
      still needs the numbered startup/error/relaunch cases.
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
      Visual OCR alignment is observed at all three scales on the 2560 × 1440
      display. Clicking the tested region opens its matching popup fully on-screen
      at each scale, and all four popup buttons respond with maintainer confirmation.
      Selection, hover, other targets and relaunch remain open.
- [ ] Offline capture/lookup/uncached translation; saved words/sentences and
      translation cache across relaunch, then shortcut/capture after reboot.
      Offline uncached sentence translation and saved-word/sentence persistence
      after app restart, offline OCR/lookup, and both shortcuts/page scan after reboot
      are maintainer-confirmed; cache persistence and saved-entry verification after
      reboot remain open.
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

Next action: resolve the native/source entries in the source worksheet and
perform the numbered PC checklist when the separate hardware is available.
The manifest
collects original sdists and source/binary archives; it does not claim complete
corresponding-source coverage. The selected compiler/SDK fail closed if absent
from the hosted image. Dictionary downloads also fail if the daily snapshot
moves; supply the pinned snapshot or deliberately rebuild with new hashes. Candidate CI may assist development before publication CI is enabled.
Run `37720960120` rejected changed upstream KANJIDIC2 bytes before freezing.
The deliberate replacement has creation date 2026-10-08 and SHA-256
`5fc25740c21180e0c2983d3ed546a8009d7891d9dceb4714cd36dd528be2bb58`.
JMdict remains the pinned 2026-10-07 snapshot. Pinned asset downloads now run
before compilation; a private candidate also retains the original two gzip
files in `windows-dictionary-snapshots.tar.gz`. For a later rebuild, extract
that verified archive into `apps/desktop/src-tauri/resources/ocr/assets/`;
changed upstream bytes are still rejected and never automatically repinned.
Replacement run `37780050429` at `2f41b64` rejected a subsequently moved JMdict
download before compilation. Windows CI now restores the two original gzip
files from the exact private candidate's dictionary archive, SHA-256
`5c0a690c74b1d361b061b0ec02b7bace314e1cdcdc985c1ed4675270c15e0db8`,
checks draft/asset identity and both manifest hashes, and retains a seed record.
Only dictionary originals are reused; no Windows runtime/source approval is
inherited. Authentication stays in an HTTP header and is stripped on redirects
to GitHub's signed asset storage. Both new Windows-only verification/seed scripts
are explicitly allowed by the macOS reuse guard; shared runtime inputs remain
protected. No macOS packaging recipe or publisher is changed.
Hosted run `37721943728` passes the complete installed frozen-learning smoke,
including actual loaded DLL paths and saved-data/cache restart. The recipe
retains required `torch.testing` imports, excludes OS DbgHelp/WinTrust/UCRT/API
copies and unused codecs, preserves app-local VC libraries, and isolates
Windows PowerShell diagnostics from inherited PS7 modules. Known setuptools
and Tauri outputs are restored before enforcing clean committed source.
The hosted Windows Server 2022 result does not establish Windows 11 hardware,
browser/SmartScreen, screen capture, shortcuts, upgrade/uninstall or display
scaling coverage. The maintainer must report those results on the separate PC.
Public distribution also requires completing native source/terms bindings and
resolving Intel MKL/IPP compatibility or testing compatible source-built
replacements. The source/rebuild worksheets record exact remaining work;
no replacement build or human installer approval is claimed.
