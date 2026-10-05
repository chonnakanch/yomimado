# First macOS pre-release gate

The Apple Silicon `.app` and `.dmg` built by
`scripts/build-macos-prerelease.sh` are **private test artifacts** until the
remaining steps below pass. The DMG is intended for GitHub Releases, not the
Mac App Store. Do not attach the current unsigned installer to a GitHub
release or upload it as a downloadable CI artifact.

## Completed automated checks

- The build uses fixed Manga OCR and translation-model weight SHA-256 values.
- The build checks the installed Python packages against
  `services/ocr/requirements-macos-release.txt`; Rust and JavaScript use
  their tracked lockfiles.
- Detector ONNX weights are user-installed and must not appear in the bundle.
- `scripts/generate-macos-notices.py --strict` inventories compiled/frozen
  dependencies and places a notice file for each one in the bundle.
- `scripts/verify-macos-bundle.py` checks required assets and notices, their
  checksums, and absence of detector weights and sample artwork. Manga OCR's
  required warm-up image is replaced with a generated blank image.
- The package includes EDRDG/CC BY-SA licence text and a monthly
  [dictionary update procedure](dictionary-updates.md).
- The private DMG passed disk-image verification. Its mounted app launched and
  passed local OCR, word/kanji lookup, Sudachi tokenization, and on-demand
  translation smoke tests on the development Mac.

## Still required before public distribution

1. Install a valid **Developer ID Application** certificate and supply
   notarization credentials outside the repository. Tauri accepts
   `APPLE_SIGNING_IDENTITY` and either an App Store Connect API key
   (`APPLE_API_ISSUER`, `APPLE_API_KEY`, `APPLE_API_KEY_PATH`) or Apple ID
   notarization variables. Never commit the certificate, private key, or
   passwords.
2. Build a signed app with hardened runtime, submit it to Apple for
   notarization, and staple the ticket. Verify the final artifact with
   `codesign --verify --deep --strict` and `spctl --assess --type execute`.
3. Inspect the exact signed DMG again with `scripts/verify-macos-dmg.sh` and
   run OCR, JMdict/KANJIDIC2, saved-data, and translation smoke tests on it.
4. Test first launch, model import, and Screen Recording permission on a clean
   Apple Silicon macOS installation. Document the install
   instructions and the dictionary refresh date in release notes.
5. Publish the corresponding source for the exact binary revision alongside
   the GitHub Release, with the GPL-3.0-only project licence and bundled
   third-party notices. Review the generated manifest before publishing;
   automated completeness checks are not a legal compatibility opinion.

Only after these gates pass should a GitHub Actions workflow automatically
build downloadable macOS artifacts. It must fail closed when signing or
notarization credentials are missing, verify the final bundle, and never
publish an unsigned fallback. A Windows release remains a separate milestone.

References: [Apple notarization requirements](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution),
[Tauri macOS signing](https://v2.tauri.app/distribute/sign/macos/), and
[Tauri GitHub Actions guidance](https://v2.tauri.app/distribute/pipelines/github/).
