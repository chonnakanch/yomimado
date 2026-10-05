# First macOS pre-release gate

Distribution: an **Apple Silicon DMG on GitHub Releases**, for macOS **14 or
later**, outside the Mac App Store. The default output of
`scripts/build-macos-prerelease.sh` is a **private test artifact**. Do not upload
it to a Release or as a downloadable CI artifact. Detector ONNX weights must
remain user-installed.

## Status — 2026-10-05

- [x] Private DMG builds; previous mounted bundle passed OCR, dictionaries,
      kanji, tokenization and translation on the development Mac.
- [x] Pin the Python environment and model checksums; use Cargo/npm lockfiles.
- [x] Replace Xcode Python with source-built CPython 3.11.17 and static OpenSSL
      3.5.9/liblzma 5.8.4. Capture original sources, recipe and embedded notices;
      repeat the frozen DMG smoke with that isolated runtime.
- [x] Exclude detector weights and example artwork/fonts; preserve EDRDG/model
      notices and dictionary update instructions.
- [x] Audit package inventory and add missing detector/bootloader records and
      native binary provenance. See [source review](macos-source-review.md).
- [x] Prepare a separate fail-closed `--release` path, nested signing, explicit
      notarization/stapling and signature/source verification.
- [x] Set macOS 14 minimum from actual frozen binaries; check architecture
      and deployment targets in the mounted DMG.
- [x] Replace the public OpenCV wheel with a source-pinned image/ONNX-only
      build, retaining ONNX detection/geometry and removing the FFmpeg dependency
      chain. Preserve static notices and generate its matching source archive.
- [ ] Complete native licence/source delivery for the remaining frozen
      interpreter/libraries and all software components. The OpenCV replacement
      and package inventory pass do not clear this entire gate.
- [x] Gather checksum-verified source candidates for the locked Rust/JavaScript
      inputs and available Python sdists; add the missing full libquadmath LGPL
      text. Final native sources/build recipes and source-delivery review remain
      open; see [the follow-up audit](macos-source-review.md).
- [ ] Install a Developer ID Application signing identity and authenticate a
      `notarytool` Keychain profile. Apple Developer account is available; signing
      is not configured. Last local check: **0 valid signing identities**.
- [ ] Build and verify the signed/notarized candidate and run the frozen-service
      smoke on that exact DMG.
- Fresh-macOS install test: **skipped at the maintainer's request on
  2026-10-05**; no clean Mac is available. This is a waiver, not a passed test.
- [ ] Complete the remaining [installed-app test record](macos-clean-mac-test.md)
      on the existing Mac: Gatekeeper launch, model import and Screen Recording.
- [ ] Publish source archives, notices, hashes, dictionary refresh dates and
      release notes alongside the verified DMG.
- [ ] Only then implement the GitHub Actions release workflow. No workflow or
      unsigned fallback artifact has been added.

## Development-Mac verification — 2026-10-05

- Previous baseline: 55 desktop and 36 Rust tests passed. The OpenCV change
  passes 47 OCR-service tests. Runtime/source preparation passes 48 release-tool
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
  `48357066ab8e871775b20d92fb50e5cd5e61b7df0cd198b11c8b721d403e97ab`.
  The runtime build entrypoint, three original archives and 11 licence/notice
  texts are retained; frozen interpreter inputs match the recorded hashes.
- Bundled JMdict/KANJIDIC2 header dates: **2026-09-27**.
- Private DMG SHA-256:
  `8177974553d91d5399c2ef57fe8c674e30d1609bbdd206a3f03a9a531cf672dc`.
  This artifact was built from the preparation working tree based on
  `9da9c0f`; it is unsigned/private and is
  not a public candidate. The release path requires a clean committed tree.

These results do not clear the native-source, signing/notarization or remaining
installed-app checks above. Fresh-machine behavior remains unverified and must
be disclosed in the pre-release notes. Cold frozen startup gets a bounded
180-second allowance; the smoke surfaces startup diagnostics and cleans its
process group/test volume.

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
and embedded notices with that record. Signing/relocation changes final bytes.

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

## Credentials — local Keychain only

Use an Apple Developer Program account with a **Developer ID Application**
certificate, including its associated private key, installed through Keychain
Access. Create the CSR/private key locally and install the issued certificate;
never send keys/passwords in chat or put them in this repository. A Developer
ID Installer certificate is not needed for this DMG (it is for signed PKGs).

The account is available but local signing setup remains pending. Complete
these steps yourself on the build Mac:

1. In Keychain Access, choose Certificate Assistant → Request a Certificate
   from a Certificate Authority. Enter your email and a key name, leave the CA
   email blank, and save the CSR outside the repository. The private key stays
   in your Keychain. See [Apple's CSR instructions](https://developer.apple.com/help/account/certificates/create-a-certificate-signing-request/).
2. In the Developer account's Certificates, Identifiers & Profiles, create a
   **Developer ID Application** certificate using that CSR. Apple's manual
   certificate flow requires the Account Holder role. Download the `.cer` and
   double-click it to install; confirm the matching private key in Keychain's
   My Certificates. See [Apple's certificate instructions](https://developer.apple.com/help/account/certificates/create-developer-id-certificates/).
3. Run `rtk security find-identity -v -p codesigning` locally. It must list a
   valid Developer ID Application identity. Then configure notarization below.
   Keep keys, credentials and account details out of chat and git.

Use `xcrun notarytool store-credentials YomiMado-notary` in your own Terminal
and answer its local interactive prompts. An App Store Connect API key or an
Apple ID app-specific password may authenticate notarization; keep any API key
file outside the repository. Do not put a password on a shell command line or
record it in shell history. Store credentials in the Keychain profile, then
set these **non-secret selectors** in the build Terminal:

```sh
export APPLE_SIGNING_IDENTITY='Developer ID Application: YOUR NAME (TEAMID1234)'
export YOMIMADO_APPLE_TEAM_ID='TEAMID1234'
export YOMIMADO_NOTARY_PROFILE='YomiMado-notary'
rtk services/ocr/build/release-venv/bin/python scripts/macos-release.py preflight
```

Replace the example team and identity with real values. Preflight checks the
identity type/team, Keychain availability and notary authentication before
building. It prints no credential-tool output on failure. The release uses
`notarytool --keychain-profile`; it suppresses Tauri's separate environment
notary path, which can warn and continue when unauthenticated. All failures
stop the release script. Do not retry with ad-hoc signing, bypass Gatekeeper,
disable SIP, or clear quarantine to obtain a release sign-off.

## Source preparation and signed candidate

Read [the source review](macos-source-review.md) and resolve its native-input
gap first. After committing release changes, generate an exact review worksheet
from the regenerated notices:

```sh
rtk services/ocr/build/release-venv/bin/python scripts/macos-release.py source-template apps/desktop/src-tauri/resources/ocr/notices --revision "$(rtk git rev-parse HEAD)" > /private/tmp/source-delivery.json
```

Move/fill that worksheet in your local source delivery directory, with actual
source archives, their hashes, native notice additions, `BUILD.md`, and the
reviewer/date. No entry may remain a placeholder. It covers the entire
conservative inventory, including native code; it is bound to both inventory
hashes and the exact project commit. Set `YOMIMADO_SOURCE_DIR` to this directory
(outside git). Set `YOMIMADO_SMOKE_DETECTOR_MODEL` to your separately installed
ONNX file for the frozen smoke (it is never copied into the bundle). The build
rejects a dirty project/detector tree. The validator
checks records/files/hashes; the reviewer must inspect source contents,
patches/build recipes and licence compatibility.

```sh
rtk bash scripts/build-macos-prerelease.sh --release
```

The release path signs every Mach-O runtime binary and framework inside out,
then seals the app with a secure timestamp and hardened runtime. It adds no
library-validation or unsigned-memory exemptions. Apple must accept an app ZIP
submission; the app ticket is stapled and validated. The DMG is then created,
signed, separately submitted, accepted and stapled. The final mounted bundle
must pass:

- expected Developer ID authority/team and timestamp for all nested Mach-O code;
- Apple Silicon slices and compatible minimum deployment targets;
- `codesign --verify --deep --strict`, app/DMG `stapler validate`, and app/DMG
  `spctl` assessments;
- strict asset/notice checks, no detector weights/artwork and source-delivery
  equality/coverage/hashes;
- the frozen-service smoke on that exact mounted signed app.

Accepted-submission IDs/status and final DMG SHA-256 are saved alongside the
candidate under ignored `target/release/bundle/releasable/`. These do not
replace the remaining installed-app/manual gate. Signed execution is still
unverified until credentials are available: if hardened-runtime loading fails,
diagnose the exact library/signature before adding any entitlement.

To re-verify the exact candidate:

```sh
rtk bash scripts/verify-macos-dmg.sh /absolute/path/YomiMado_0.1.0_aarch64.dmg services/ocr/build/release-venv/bin/python --release
```

Mount read-only using Disk Utility or `hdiutil attach`, then point this at the
mounted app and your separately obtained detector file:

```sh
rtk services/ocr/build/release-venv/bin/python scripts/smoke-macos-bundle.py /Volumes/YomiMado/YomiMado.app --detector-model /absolute/user/path/comictextdetector.pt.onnx
```

The smoke uses temporary databases, an empty Hugging Face cache, offline model
flags and a generated vertical `学校へ` image. It exercises health, real OCR
geometry, Sudachi, JMdict/KANJIDIC2, translation, and saved word/sentence/cache
survival across a service restart. It runs the frozen service outside the repo
and does not touch existing app learning data. It does not prove GUI first
launch, Keychain/Gatekeeper behavior or Screen Recording permission; use the
installed-app record for those. The detector remains outside the app and source
pack.

## Future GitHub Actions gate

Do not implement or activate a Release-artifact workflow until the preceding
installer gates have passed. Then use a protected release environment with
required reviewer approval and signing/notary secrets available only to trusted
tag/manual runs. Never expose them to pull-request code or fork builds.

Use commit-pinned actions and read-only default token permissions; grant
`contents: write` only to the publish job after verification. Import the
encrypted Developer ID `.p12` into an ephemeral keychain, authenticate
notarytool with environment secrets/API key files in runner temp, mask sensitive
values, disable shell tracing, and clean keychains/key files in an always-run
cleanup. Require all certificate/password/team/notary inputs before building;
never fall back to unsigned/ad-hoc output. Reuse the release/source verifiers
and frozen smoke; upload only the exact verified DMG, source archives, notices
and hashes after all jobs succeed. Verify the artifact digest when transferring
between jobs. Capture installed-app sign-off for changes affecting packaging,
permissions, runtime or signing. Retain the explicit fresh-machine test waiver
and unverified limitation until that test is actually performed. Keep Windows
as a separate milestone.

References: [Apple notarization workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow),
[Tauri macOS signing](https://v2.tauri.app/distribute/sign/macos/),
[PyInstaller 6.16.0 signing](https://pyinstaller.org/en/v6.16.0/feature-notes.html#macos-binary-code-signing).
