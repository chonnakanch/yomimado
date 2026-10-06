# First macOS pre-release gate

Distribution: a downloadable **Apple Silicon DMG on GitHub Releases**, for
macOS **14 or later**, outside the Mac App Store.

On 2026-10-05 the maintainer chose a free **unnotarized hobby release**.
Developer ID signing and Apple notarization are optional and are no longer
release gates. This replaces the earlier signed-only distribution requirement.
Users must explicitly allow the app through macOS Gatekeeper. Apple Silicon
apps require a valid local ad-hoc bundle signature and resource seal; these do
not identify a publisher or provide Apple notarization. Detector ONNX weights
remain **user-installed**.

The default build remains a **private test artifact**. `--release` is the
explicit hobby candidate path, with source and exact-DMG checks. Neither path
publishes anything automatically. Do not upload a private build or an
incomplete candidate.

## Status — 2026-10-06

- [x] Private DMG builds and passes mounted-bundle OCR, dictionary, kanji,
      tokenization, translation and persistence smoke tests on the development Mac.
- [x] Pin runtime, package versions and model hashes; use Cargo/npm lockfiles.
- [x] Replace Xcode Python with source-built CPython 3.11.17 and static OpenSSL
      3.5.9/liblzma 5.8.4; preserve original sources and embedded notices.
- [x] Replace the FFmpeg-bearing OpenCV wheel with a source-pinned image/ONNX
      build; preserve its static notices and exact changes/build recipe.
- [x] Replace NumPy's public wheel with an exact-source Accelerate build;
      remove its OpenBLAS/GCC/libquadmath dylibs and retain embedded notices.
- [x] Record verified source/notice evidence for all frozen native inputs:
      **114 of 114 unique native inputs**. See the
      [technical review record](../THIRD_PARTY_LICENSES/macos-native-review.json).
- [x] Exclude detector weights and sample artwork/fonts; preserve EDRDG/model
      credits and dictionary update instructions.
- [x] Gather checksum-verified dependency source candidates and add the missing
      full libquadmath LGPL licence text.
- [x] Make the hobby candidate explicit and fail closed on missing source
      clearance, incorrect distribution metadata or failed bundle/smoke checks.
- [x] Complete native source/notice review for all **114 unique native inputs**.
      Missing embedded notices are retained; exact sources and input hashes are
      verified. GEOS shared-library replacement passes. Optional Pillow/vision
      codecs, training-only wandb binaries and compiled Tomli are removed.
- [x] Prepare the complete source-delivery copy: 75 archives, all 477 entries,
      2,332 source-only assets omitted and 9 vendor checksum maps updated.
      Original inputs stay private; retained content comparison and locked
      offline Cargo dependency resolution pass. App packaging is unchanged.
- [x] Record maintainer source/licence approval as **chonnakanch**, 2026-10-06,
      for clean project revision `042360e`. The approved `source-delivery.json`
      passes all 477 entry, archive hash and notice checks. Full rebuild from
      only the filtered source package remains unverified, as disclosed before
      approval; the project frontend/Rust and filtered Manga OCR rebuild checks
      pass. Approval does not mark installed-app tests or publication complete.
- [x] Build the source-cleared hobby candidate from clean commit `042360e`;
      exact mounted DMG/bundle and frozen-service smoke pass. SHA-256:
      `4bfd303f2a566c8669d0a80ca3c394099cae8bfba48b31313713ada88a1cf1ff`.
- Fresh-macOS installation: **skipped at the maintainer's request on 2026-10-05**;
  no clean Mac is available. This is a waiver, not a passed test.
- [ ] Complete the [existing-Mac installed-app record](macos-clean-mac-test.md):
      browser quarantine, per-app Gatekeeper approval, model import and Screen
      Recording. Preserve existing learning data and permissions.
- [ ] Replace the `042360e` candidate: browser quarantine/hash and Finder copy
      passed, but first launch reported **damaged**. Its linker-only signature
      lacks the app resource seal. Hobby packaging now requests Tauri's local
      ad-hoc signing; mounted verification requires the seal and verifies every
      Mach-O signature. Rebuild and repeat the installer tests before release.
- [x] Draft [pre-release notes](macos-prerelease-notes.md) with installation,
      detector import, permissions, data credits and known limitations.
- [ ] Finalize release notes with unnotarized status, install steps, fresh-Mac
      limitation, source commit, dictionary dates, download links and hashes.
- [ ] Publish the verified DMG, matching source delivery and notices together.
- [ ] Only after the installer gates pass, add the GitHub Actions release build.

## Development-Mac verification — 2026-10-06

- Previous baseline: 55 desktop and 36 Rust tests passed. The OpenCV change
  passes 47 OCR-service tests. NumPy numerical suites pass 1,820 tests (12
  skipped, 1 expected failure). The hobby/source preparation passes 63 release-tool
  tests, including altered interpreter, native replacements/supplements, frozen-input, recipe and licence rejection
  cases. All seven selected CPython test groups pass (2,114 tests run, 124
  skipped): SSL, LZMA, hashing, SQLite, ctypes, decimal and Expat.
- Frontend production build, Rust formatting, Python lint/format, Prettier and
  shell syntax checks passed. The private Apple Silicon native build completed.
- The rebuilt private DMG passed disk-image, asset/notice, native inventory,
  architecture/deployment-target and absolute development-library-link checks.
- Its mounted frozen service passed synthetic vertical `学校へ` OCR with
  geometry, Sudachi, JMdict, KANJIDIC2, explicit translation, and saved word,
  sentence and translation-cache persistence across a service restart.
- Inventory: 362 software/source components (280 Rust, 73 Python, 5 JavaScript,
  detector, CPython, OpenSSL and liblzma source), 114 unique native input binaries
  plus 9 aliases (123 paths, down from 310). All native reviews are hash-verified.
  Corresponding-source worksheet: 477 entries; final delivery sign-off is separate.
- The regenerated source report for clean commit `02c0b3b` has **477 entries,
  75 distinct archives, zero unresolved entries and 114 verified native inputs**.
  The private `source-delivery.worksheet.json` is fully populated, with matching
  archive hashes, notice paths and technical licence evidence; `BUILD.md`
  provides rebuild/replacement instructions. Reviewer/date remain blank until
  the complete source-delivery review and source-only asset cleanup finish.
- The former NumPy wheel received its missing full libquadmath LGPL text;
  the current Accelerate build contains no libquadmath and omits that supplement. Cargo source archives include the original crate archives
  and vendor tree; their current hashes are in `source-candidates.json`.
- OpenCV source delivery SHA-256:
  `b426f96f5620aa310dd0971d0a247e5b0d81f880412aed43d665f141f9fd3f12`.
  Its original source, exact modifications, recipe copies and build record
  match. The installed custom wheel has no video APIs/external dylib links;
  the user's ONNX model loads and performs inference. System-Cocoa highgui
  remains solely for the detector's unused `imshow` import.
- Python/OpenSSL/liblzma source delivery SHA-256:
  `09c6431422ba61a844cead37b06075ade65486b559b40fdc981f04a4240079cc`.
  The runtime build entrypoint, three original archives and 11 licence/notice
  texts are retained; frozen interpreter inputs match the recorded hashes.
- NumPy source delivery SHA-256:
  `ad1d14405aab335a1449aa2b512581c1de70619de435e2b88736e7d6235d6dcc`.
  Original NumPy 1.26.4 source, compiler/SDK, pinned build tools, Accelerate
  options, notice aggregation and installed/frozen input hashes are verified.
- New native preparation source archive SHA-256:
  `7e64a3d3cd4429ae6a0908df2a156874bb8f4b3ce48f43b2ca23781cab6bf1c6`.
  Pillow/FreeType/JPEG, torchvision, OpenMP, pinned build tools, original Tomli
  wheel, notice aggregation and binary record retained. Native Rust source
  archive SHA-256:
  `03aad3a2206b379dc8e362f63d98fa319e8542439e7e66c1bcce89ab9d4b1f58`.
- Development-Mac native smoke: parallel Torch, torchvision CPU NMS, JPEG/PNG,
  source-built fonts and the GEOS shared-library replacement pass. The 114-input
  private DMG passes frozen vertical OCR, dictionaries, tokenization,
  translation and persistence across restart. The clean-commit rebuild embeds
  the completed review documentation and Unicode notice; exact mounted-bundle,
  platform and frozen-service checks pass. SHA-256:
  `02c283479e0b60df2c10d0365e0af425fd18b9b61c31d208772bdd0744a07182`.
  Its embedded project revision is `02c0b3b` and mode is `private-test`;
  it is not a signed-off public hobby candidate.
- Bundled JMdict/KANJIDIC2 header dates: **2026-09-27**.
- Source-delivery preparation passes **70 release-tool tests** and **47 OCR
  tests**. The filtered copy preserves 156,012 compared files; every omitted
  asset has a path/hash record. Code and notice content is unchanged. The
  filtered Cargo vendor tree resolves the locked project offline. See
  `services/ocr/build/source-delivery-prepared-final/` for the worksheet,
  archive hashes, omission record, content verification, notices and `BUILD.md`.
  The original preparation worksheet remains unsigned. The separate approved
  `source-delivery.json` now records the maintainer's explicit approval under
  Git account `chonnakanch`, dated 2026-10-06. Its bytes match the candidate's
  embedded manifest; coverage/hash/notice verification passes. Size optimization
  is deferred at the maintainer's request.
- Source-package partial rebuild checks pass: frontend build from the extracted
  project using existing Node tools/dependencies; Rust checks from that project
  against the filtered vendor tree (259 crates, locked/offline); and a Manga OCR
  wheel from the filtered 0.1.16 sdist. Manga OCR's preferred `ocr.py` matches
  the installed runtime source. Complete app/all-native-dependency rebuilding
  using only the filtered package has not been verified. See the local
  `source-rebuild-verification.json`; do not claim an end-to-end source rebuild.
- The first source-cleared `unnotarized-hobby` candidate embeds clean revision
  `042360e` and the approved manifest. Its exact mounted disk-image/bundle checks
  and frozen health, vertical OCR geometry, Sudachi, JMdict, KANJIDIC2,
  translation and saved-data/cache restart smoke pass. It is available privately
  under `apps/desktop/src-tauri/target/release/bundle/releasable/` with its hash
  sidecar. Installed-app authorization/testing is pending; no public upload or
  release CI is activated. Developer ID/notarization remains optional.
- Previous private DMG SHA-256:
  `3750db3829ba9356778c9c6be8e634375494f840c0b2a9cc459268dd155871cf`.
  This artifact was built from the preparation working tree based on
  `c3be4ee`; its metadata identifies it as `private-test` and it is
  not a public candidate. The embedded review document predates the final
  NumPy technical record; final release packaging must regenerate it. The release path requires a clean committed tree.

The native review is complete. These private-build results do not clear final source-delivery or
installed-app gates. Fresh-machine behavior remains unverified.

## Source-built release runtime

Prepare the isolated runtime once on Apple Silicon with Xcode command-line
tools. This uses the existing build entrypoint:

```sh
rtk bash scripts/build-macos-prerelease.sh --prepare-runtime
rtk bash scripts/build-macos-prerelease.sh --prepare-native
rtk bash scripts/build-macos-prerelease.sh
```

Preparation downloads checksum-pinned CPython 3.11.17, OpenSSL 3.5.9 and XZ
5.8.4 sources, builds Python against static OpenSSL/liblzma, and installs the
locked packages plus source-built NumPy and the custom OpenCV wheel in
`services/ocr/build/release-venv`. The development `.venv` is separate. The standalone
`--prepare-numpy` option rebuilds only NumPy, using a separate build-tool
virtual environment. See the [NumPy recipe](macos-numpy.md).
The default build refuses Apple's Xcode interpreter or a runtime whose
recorded binary/notice/source hashes differ. Keep the ignored
`build/python-source/` records and archives for the corresponding-source
review. The mounted-bundle verifier compares frozen interpreter input hashes
and embedded notices with that record. Relocation and local ad-hoc signatures can change final bytes.
The runtime fingerprint covers only the preparation block; changing packaging
commands does not force a native rebuild. Original compile inputs remain bound.

The source archive contains original release tarballs, the exact build
entrypoint and binary/notice records. Preserve CPython's licence and the
embedded Expat, libmpdec, SHA3, BLAKE2, Mersenne Twister, dtoa and SipHash notices,
plus OpenSSL and liblzma terms. Only liblzma is linked; XZ command-line tools
and scripts are disabled. SSL certificate lookups for build downloads use the
pinned certifi package after installation. All other wheel-native sources are now reviewed. Final
delivery sign-off remains a separate release gate.

Upstream releases: [CPython 3.11.17](https://www.python.org/downloads/release/python-31117/),
[OpenSSL sources](https://openssl-library.org/source/),
[XZ 5.8.4](https://github.com/tukaani-project/xz/releases/tag/v5.8.4).

## Source preparation and hobby candidate

Read [the source review](macos-source-review.md). Generate a worksheet from the
actual regenerated inventory and clean source commit:

```sh
rtk services/ocr/build/release-venv/bin/python scripts/macos-release.py source-template apps/desktop/src-tauri/resources/ocr/notices --revision "$(rtk git rev-parse HEAD)" > /private/tmp/source-delivery.json
```

Complete it in an ignored local source-delivery directory, with verified source
archives, hashes, licence/notice evidence, `BUILD.md` and final reviewer/date.
The technical native-review record can supply completed evidence; it does not
approve the whole delivery. The current conservative worksheet covers every
software/native entry. It must not contain placeholders.

Set `YOMIMADO_SOURCE_DIR` to that reviewed directory and
`YOMIMADO_SMOKE_DETECTOR_MODEL` to your separately installed ONNX file.
The detector remains outside the app and source delivery. Then run:

```sh
rtk bash scripts/build-macos-prerelease.sh --release
```

This path requires no Apple account, key or password. It strips Apple signing
credentials from the bundle command, explicitly selects local ad-hoc identity
`-` to seal the app before DMG creation, records `unnotarized-hobby` distribution
metadata, checks the clean project/detector revision and source delivery, and
runs the mounted DMG verifier plus frozen-service smoke. Candidate files are
copied to ignored `target/release/bundle/releasable/` only after success. Missing
source clearance or a failed check stops the build; it never falls back to the
private artifact. Manual installed-app sign-off is still required.
Mounted hobby verification also requires a signed resource seal and valid outer
and nested Mach-O signatures. These integrity checks do not claim Apple trust.

Reverify a candidate with the same reviewed source directory and detector path:

```sh
rtk bash scripts/verify-macos-dmg.sh /absolute/path/YomiMado_0.1.0_aarch64.dmg services/ocr/build/release-venv/bin/python --hobby-release
```

The frozen smoke runs outside the repository with temporary databases, an empty
Hugging Face cache and offline model flags. It checks real vertical `学校へ`
OCR geometry, Sudachi, JMdict/KANJIDIC2, explicit translation and saved
word/sentence/cache persistence after restart. It does not prove Finder launch,
Gatekeeper approval, model-import UI or Screen Recording; those need the
installed-app record.

For a browser-downloaded unnotarized app, follow Apple's per-app **Open Anyway**
flow in System Settings → Privacy & Security after the initial block. Do not
remove quarantine or globally disable Gatekeeper to claim a pass. A damaged or
malware warning requires investigation. See
[Apple's instructions](https://support.apple.com/en-us/102445).

## Optional Developer ID build

The existing `--developer-id-release` path remains available if the maintainer
later chooses paid Apple distribution. It requires a local Developer ID
Application identity and authenticated notarytool Keychain profile. Its nested
signatures, Apple acceptance, stapling and Gatekeeper assessments remain strict;
it cannot fall back to a hobby build. Setup is optional for this release.
Keep all private keys/passwords out of chat, source control and command history.

## Future GitHub Actions gate

Do not implement or activate a Release-artifact workflow until source clearance,
exact-DMG verification and installed-app sign-off are complete. The hobby target
needs no signing/notarization secrets. Use pinned actions, read-only default
permissions and a protected release environment with approval for publishing.
Grant `contents: write` only to the publish job. Build from an exact clean
commit, reuse source/bundle/distribution verifiers and the frozen smoke, and
verify artifact digests between jobs. Upload only the verified DMG, matching
source delivery, notices and hashes after all required jobs succeed. Never
publish private outputs or detector weights. Keep the fresh-Mac waiver in the
release notes and require renewed installed-app checks when packaging or
permissions change. Windows remains a separate milestone.
