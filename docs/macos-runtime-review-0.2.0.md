# macOS 0.2.0 runtime/source review candidate

Prepared on 2026-10-16 from source
`fae4d286619543014edb8aff6302fd3c864783a1`. **Source/licence delivery approved by chonnakanch on 2026-10-16.**
This review is for refreshing the private CI runtime seed. It is separate from
installed-app acceptance and protected publication approval.

## What changed

- YomiMado's GPL source contains the approved UI redesign, OCR boundary recovery,
  cold-start capture fix and exclusive recognition admission.
- The five app version files now agree on `0.2.0`.
- Dependency versions, build recipes, selected licences and bundled data/model
  inputs are unchanged from the reviewed `42edd4e` runtime seed.
- Both exact dependency/native inventory hashes match the reviewed seed. All 476
  non-project source entries remain identical; all 74 dependency archives retain
  their exact hashes. The complete delivery has 477 entries and 75 archives.
- The new project archive matches the exact tracked Git tree, including build
  recipes and synthetic tests. User-local design references, detector weights and
  manga screenshots are excluded.

Project archive: `yomimado-fae4d286619543014edb8aff6302fd3c864783a1.tar.gz`.
SHA-256: `702fb1457dbc8d36af597182e053889d9814a75c0269f456ae7ed269de6d3e07`.

## Verification completed

- Private macOS DMG builds and passes mounted bundle/platform validation.
- App resource seal and all Mach-O ad-hoc signatures pass verification.
- Frozen bytecode for seven modules matches the committed source, including the
  changed OCR admission, geometry and recognition modules.
- Offline frozen-service smoke passes health, synthetic vertical OCR geometry,
  Sudachi, JMdict, KANJIDIC2, local translation and saved-data/cache restart.
- Local source checks pass 172 frontend tests, 61 native tests, 229 release-tool
  tests and the frontend production build.
- All 75 source-archive hashes verify. Both inventory hashes match the reviewed
  seed, and the project archive has exactly the tracked files for this commit.

Private DMG SHA-256:
`e804cce042c16e3eb1a392861e4c3a75e9f2acb9b7df557794b20e66c0afef02`.
This private test DMG is not the future hosted release installer. Adding approved
source metadata and release-mode notices produces a separate seed/candidate hash.

## Retained limits

Dependency advisories in the existing security review remain unresolved. This
refresh does not claim to patch them. Rebuilding the entire application using only
the filtered corresponding-source delivery remains unverified. macOS is ad-hoc
signed and unnotarized; no Developer ID/notarization claim is made. Exact new
macOS/Windows installed-app acceptance, physical mixed-DPI checks and protected
publication review remain separate.

The owner explicitly answered “Approve source/licence delivery only”. The manifest
records chonnakanch and 2026-10-16 for this exact scope and retains the prior review
as historical evidence. This permits preparation of the replacement private seed
and updated hash pins; it does not approve publication or installed-app behavior.

Local evidence is retained under ignored
`services/ocr/build/macos-runtime-refresh-fae4d28/`: `source-candidate/`,
`source-content-verification.json`, `frozen-source-verification.json`,
`private-candidate.json`, `signature-verification.log`, and `mounted-smoke.log`.
The private DMG is `seed/YomiMado_0.2.0_aarch64.dmg`.

## Approved seed upload

The approved-source seed and both archives were uploaded to the unpublished
[private CI draft](https://github.com/chonnakanch/yomimado/releases/tag/untagged-1cd1cb337b8446f45a1d).
GitHub displays all three exact SHA-256 values recorded in the
[current seed record](macos-runtime-seed.md#historical-020-preparation--2026-10-16).
The final seed DMG SHA-256 is
`54623c751236029039c7ea3911f35b4b1aa8f1d2127ca23b110473c12bb32d93`.
Its mounted embedded source manifest matches the approved delivery, both inventory
hashes match the reviewed baseline, and the seven frozen modules match `fae4d28`.
The source-approved build reran the offline synthetic smoke successfully.
