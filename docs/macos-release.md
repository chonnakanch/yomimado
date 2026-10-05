# First macOS pre-release gate

Distribution: a downloadable **Apple Silicon DMG on GitHub Releases**, for
macOS **14 or later**, outside the Mac App Store.

On 2026-10-05 the maintainer chose a free **unnotarized hobby release**.
Developer ID signing and Apple notarization are optional and are no longer
release gates. This replaces the earlier signed-only distribution requirement.
Users must explicitly allow the app through macOS Gatekeeper. Apple Silicon
binaries may carry local ad-hoc signatures; these do not identify a publisher
or provide Apple notarization. Detector ONNX weights remain **user-installed**.

The default build remains a **private test artifact**. `--release` is the
explicit hobby candidate path, with source and exact-DMG checks. Neither path
publishes anything automatically. Do not upload a private build or an
incomplete candidate.

## Status — 2026-10-05

- [x] Private DMG builds and passes mounted-bundle OCR, dictionary, kanji,
      tokenization, translation and persistence smoke tests on the development Mac.
- [x] Pin runtime, package versions and model hashes; use Cargo/npm lockfiles.
- [x] Replace Xcode Python with source-built CPython 3.11.17 and static OpenSSL
      3.5.9/liblzma 5.8.4; preserve original sources and embedded notices.
- [x] Replace the FFmpeg-bearing OpenCV wheel with a source-pinned image/ONNX
      build; preserve its static notices and exact changes/build recipe.
- [x] Record verified native source/notice evidence for those two builds:
      **59 of 152 unique native inputs**. See the
      [technical review record](../THIRD_PARTY_LICENSES/macos-native-review.json).
- [x] Exclude detector weights and sample artwork/fonts; preserve EDRDG/model
      credits and dictionary update instructions.
- [x] Gather checksum-verified dependency source candidates and add the missing
      full libquadmath LGPL licence text.
- [x] Make the hobby candidate explicit and fail closed on missing source
      clearance, incorrect distribution metadata or failed bundle/smoke checks.
- [ ] Complete the remaining native source/notice review and final delivery
      review. **93 unique native inputs** remain, including NumPy/GCC/OpenBLAS,
      Pillow/torchvision codecs, PyTorch, GEOS and wandb tools. Package source
      candidates are not final clearance; see [source review](macos-source-review.md).
- [ ] Build a source-cleared hobby candidate from a clean commit; verify that
      exact mounted DMG and its frozen service, then retain its SHA-256.
- Fresh-macOS installation: **skipped at the maintainer's request on 2026-10-05**;
  no clean Mac is available. This is a waiver, not a passed test.
- [ ] Complete the [existing-Mac installed-app record](macos-clean-mac-test.md):
      browser quarantine, per-app Gatekeeper approval, model import and Screen
      Recording. Preserve existing learning data and permissions.
- [x] Draft [pre-release notes](macos-prerelease-notes.md) with installation,
      detector import, permissions, data credits and known limitations.
- [ ] Finalize release notes with unnotarized status, install steps, fresh-Mac
      limitation, source commit, dictionary dates, download links and hashes.
- [ ] Publish the verified DMG, matching source delivery and notices together.
- [ ] Only after the installer gates pass, add the GitHub Actions release build.

## Development-Mac verification — 2026-10-05

- Previous baseline: 55 desktop and 36 Rust tests passed. The OpenCV change
  passes 47 OCR-service tests. The hobby/source preparation passes 54 release-tool
  tests, including altered interpreter, frozen-input, recipe and licence rejection
  cases. All seven selected CPython test groups pass (2,114 tests run, 124
  skipped): SSL, LZMA, hashing, SQLite, ctypes, decimal and Expat.
- Frontend production build, Rust formatting, Python lint/format, Prettier and
  shell syntax checks passed. The private Apple Silicon native build completed.
- The rebuilt private DMG passed disk-image, asset/notice, native inventory,
  architecture/deployment-target and absolute development-library-link checks.
- Its mounted frozen service passed synthetic vertical `学校へ` OCR with
  geometry, Sudachi, JMdict, KANJIDIC2, explicit translation, and saved word,
  sentence and translation-cache persistence across a service restart.
- Inventory: 369 software/source components (280 Rust, 80 Python, 5 JavaScript,
  detector, CPython, OpenSSL and liblzma source), 152 unique native input binaries
  plus 36 aliases (188 paths, down from 310). Corresponding-source worksheet:
  522 entries, still unreviewed as a complete delivery.
- Dependency source candidates cover 366 entries with 85 independently hashed
  archives. Their report matches the regenerated inventory hashes. The collector
  also exports the exact clean project commit and filtered detector source.
  Complete source-delivery review and native/PyTorch provenance remain pending.
- Full libquadmath LGPL text in the rebuilt mounted DMG matches its pinned
  upstream notice. Cargo source archives include the original crate archives
  and vendor tree; their current hashes are in `source-candidates.json`.
- OpenCV source delivery SHA-256:
  `b426f96f5620aa310dd0971d0a247e5b0d81f880412aed43d665f141f9fd3f12`.
  Its original source, exact modifications, recipe copies and build record
  match. The installed custom wheel has no video APIs/external dylib links;
  the user's ONNX model loads and performs inference. System-Cocoa highgui
  remains solely for the detector's unused `imshow` import.
- Python/OpenSSL/liblzma source delivery SHA-256:
  `929cff6c903e74d0c4bf16a27a8544dd31bbf77bb6f0bce91558c037fa660137`.
  The runtime build entrypoint, three original archives and 11 licence/notice
  texts are retained; frozen interpreter inputs match the recorded hashes.
- Bundled JMdict/KANJIDIC2 header dates: **2026-09-27**.
- Private DMG SHA-256:
  `5c730340eab6cccd666f2f467f5b381321fa8806abad7e437ef85e58ad1556db`.
  This artifact was built from the preparation working tree based on
  `a5b1738`; its metadata identifies it as `private-test` and it is
  not a public candidate. The release path requires a clean committed tree.

These private-build results do not clear the remaining source-delivery or
installed-app gates. Fresh-machine behavior remains unverified.

## Source-built release runtime

Prepare the isolated runtime once on Apple Silicon with Xcode command-line
tools. This uses the existing build entrypoint:

```sh
rtk bash scripts/build-macos-prerelease.sh --prepare-runtime
rtk bash scripts/build-macos-prerelease.sh
```

Preparation downloads checksum-pinned CPython 3.11.17, OpenSSL 3.5.9 and XZ
5.8.4 sources, builds Python against static OpenSSL/liblzma, and installs the
locked packages plus the custom OpenCV wheel in
`services/ocr/build/release-venv`. The development `.venv` is separate.
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
pinned certifi package after installation. Other wheel-native sources and final
delivery review remain separate release gates.

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
credentials from the bundle command, records `unnotarized-hobby` distribution
metadata, checks the clean project/detector revision and source delivery, and
runs the mounted DMG verifier plus frozen-service smoke. Candidate files are
copied to ignored `target/release/bundle/releasable/` only after success. Missing
source clearance or a failed check stops the build; it never falls back to the
private artifact. Manual installed-app sign-off is still required.

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
