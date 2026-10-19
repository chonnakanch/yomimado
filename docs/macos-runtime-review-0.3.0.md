# macOS 0.3.0 runtime and source review

Source revision: `f1b4fbaa8980ff0df0a1abf6f5a93df058f4678e`.
The owner explicitly answered **“Approve source/license delivery as chonnakanch”**
on 2026-10-19. This approves the prepared source delivery only; installer
acceptance and protected publication approval remain separate.

The original unsigned worksheet SHA-256 is
`e3394c6c81ebe77aa93deab23ac53978906f09dfb16d546e8f5141ae24d84028`.
The separate approved manifest SHA-256 is
`1d5ea84b2372069bb01926971eeb81a239dd29af6ee1feac5b91572822ed9965`.

## Changed inputs and verification

- Lindera 6.0.0/IPADIC replaces the Sudachi extension and Fugashi/MeCab inputs.
  All 111 retained native input hashes match previous technical evidence; the
  new native review covers 112 unique inputs.
- The corresponding sources retain the complete Lindera workspace, all 399
  original locked registry crates and pinned missing-notice supplements.
  Three old crates without VCS metadata additionally require identical Rust
  source files and package identities at immutable upstream revisions.
- All nine generated IPADIC files rebuild byte for byte from the retained source
  with the pinned builder and tagged metadata. The tenth file is the matching
  tagged notice; original data COPYING remains separately preserved.
- The complete delivery has 476 entries across 76 archives, zero unresolved
  sources/notices, and 2,347 recorded omissions/vendor-map changes. Independent
  comparison checks 163,760 retained files across 107 containers without code or
  notice changes. Original and delivery archive hashes remain separate.
- All 29 frozen application modules match the exact approved source, and the
  packaged dictionary/manifest hashes pass. The original private runtime was
  built at fdaad07; f1b4fba corrects only a technical-review notice path. The
  approved seed rebuilds the native app at exact clean f1b4fba and embeds the
  matching source approval, source revision and hobby-distribution metadata.
- Mounted source coverage, bundle/platform checks, the complete app resource
  seal/all Mach-O signatures and offline frozen health/vertical OCR geometry,
  Lindera, JMdict, KANJIDIC2, translation and saved-data/cache restart pass.
- All 270 release-tool tests pass. The later import-order correction targets
  CI's Python 3.11 lint settings and changes no collected dependency input.

The runtime begins without an active local translator. Its optional Torch
translation archive is a separate CI input/download, bound by exact pins and the
embedded component manifest. macOS retains Torch; Windows remains ONNX CPU.
User-local manga and design references are outside the source export.

## Private seed files

| Input                                   | SHA-256                                                            |
| --------------------------------------- | ------------------------------------------------------------------ |
| `YomiMado_0.3.0_aarch64.dmg`            | `45175e90fcb116a9c8ac3b910f6b15a4bec8e436db94a97f09eada087d88f8eb` |
| `YomiMado_0.3.0_notices_f1b4fba.tar.gz` | `9c124cf7803f0de74a69873638825ca3ac194043b5722da9c04f59b8b39d462c` |
| `YomiMado_0.3.0_sources_f1b4fba.tar.gz` | `3d70eef8361bead6b48d056c1d8c9dd71c90bedbd64ad2dcbb9b42d4b788ceb5` |
| `YomiMado_0.3.0_translation_torch.zip`  | `e1c6a0ae58777d1eb4e8085eddff7a908fe0035e95c82178707178b7690434ef` |

The seed files are in ignored `services/ocr/build/release-0.3.0/seed-reviewed/`.
`seed-artifacts.json` records sizes and verification scope. All four uploads were independently verified in the signed-in browser, including
Draft status, exact target/label, membership and displayed SHA-256 values. The
[private draft](https://github.com/chonnakanch/yomimado/releases/tag/untagged-fd2993054a279c9bf1ae) remains unpublished. The matching CI pins are activated;
Windows dictionary inputs and the runtime/source guard remain unchanged.

## Retained limits

The native Lindera wheel is a publisher build; no source-only wheel rebuild is
attested. The complete app/all-native rebuild solely from filtered sources remains
unverified. Existing dependency advisory triage remains open. macOS is ad-hoc
signed and unnotarized. Windows requires the real release build and exact-setup
owner checks. Ollama testing is owner-run. Fresh-Mac testing is waived, not passed.
No source approval or private seed check approves new installer publication.
