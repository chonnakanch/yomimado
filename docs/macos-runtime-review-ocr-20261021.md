# OCR runtime seed and source review — 2026-10-21

Exact source: `46a5649007caf09538adb7d7d0bc4bda763c095e`, including
[PR #24](https://github.com/chonnakanch/yomimado/pull/24)'s small-selection kana
recovery and short vertical orientation correction. No dependency version, model,
data input or selected licence changes from the reviewed 0.3.0 runtime.

## Approval and delivery

The owner, `chonnakanch`, approved the prepared source/licence delivery on
2026-10-20: **“approve to do so. in order to merge this pr 24”**. The scope binds
this exact source and unsigned worksheet SHA-256
`4a6cc376572f070abb204ba1dbc7359c0d4d0ee949001c0648bb9acfc32641e3`.
The separate approved `source-delivery.json` SHA-256 is
`37eebd41afe82f538d41fafb1cba7bd4045e223b5b64c88d843f5efd616dcfd7`.
The unsigned worksheet is preserved. This source approval is separate from
exact-installer acceptance and publication.

- Complete delivery: 476 component/native entries, 76 archives and 112 unique
  native inputs; no missing source or notice. The 75 dependency archives and
  dependency/native inventories match the previous reviewed seed.
- Filtering retains preferred code, notices and build instructions, with original
  and delivery hashes recorded separately. Independent byte comparison covers
  163,791 retained files across 107 containers and 2,347 documented omissions or
  vendor-map changes; it introduces no code or notice changes.
- All 29 frozen application modules and the packaged entrypoint match the exact
  approved source. Both horizontal and vertical 学校へ fixtures recover the edge
  kana, retain geometry and request review with unknown confidence.
- The source-approved seed build passes mounted source, bundle/platform and all
  Mach-O/app-signature checks, plus offline frozen health/OCR, Lindera, JMdict,
  KANJIDIC2, translation and saved-data/cache persistence across restart.
- The optional Torch ZIP matches the embedded component manifest. Detector
  weights and user manga are excluded from the seed/source delivery.

## Verified private inputs

Label: `macos-reviewed-seed-46a5649`. The
[private draft](https://github.com/chonnakanch/yomimado/releases/tag/untagged-aebab25d653586c1ff95)
targets the exact source above and remains unpublished. Independent signed-in
browser inspection on 2026-10-21 confirms Draft status, target/label, exactly four
completed uploads and all GitHub SHA-256 digests below. Displayed sizes are
626 MB, 1.05 MB, 893 MB and 292 MB respectively; exact local byte counts are below.
Every input is smaller than 2 GiB.

| Input                                   |       Bytes | SHA-256                                                            |
| --------------------------------------- | ----------: | ------------------------------------------------------------------ |
| `YomiMado_0.4.0_aarch64.dmg`            | 656,270,895 | `19ff1c941f866df73653769f7e6b4b1c7e310509ed7e13757fd0c80e5945bf1e` |
| `YomiMado_0.4.0_notices_46a5649.tar.gz` |   1,104,586 | `0a9fcdd3e5a1c1b284e7a70f321475afc932edd905ace2fdea27fe9a92d67c6d` |
| `YomiMado_0.4.0_sources_46a5649.tar.gz` | 936,122,263 | `ae6322ed25f79226057dade2787a5acf1a61786de0714caa36008a62da5c7b71` |
| `YomiMado_0.4.0_translation_torch.zip`  | 306,394,404 | `e1c6a0ae58777d1eb4e8085eddff7a908fe0035e95c82178707178b7690434ef` |

The revision pin, macOS input label/hashes and all workflow extraction/cleanup
paths are activated together. Windows input pins and runtime guard rules are
unchanged. Pin activation does not rebuild or publish an installer.

Local evidence is retained under ignored
`services/ocr/build/runtime-seed-46a5649/`, including `source-approval.json`,
`source-delivery.worksheet.json`, `source-delivery.json`,
`frozen-source-verification.json`, `frozen-small-selection-smoke.json`,
`approved-seed-verification.json`, `seed-artifacts.json` and
`browser-verified-inputs.json`. The earlier private candidate and pre-approval
reports remain historical and are not the activated inputs.

## Pin activation checks

All 138 relevant macOS source/notice, shared release/rule and version tests pass,
as do script Ruff lint/format, pinned actionlint, local documentation links and
exact input membership/hash verification. The broader 303-test discovery has
three environment failures in unrelated probes: Torch and jaconv are absent from
the verification environment, and its OpenCV exposes video APIs excluded by the
Windows minimal-build probe. The reviewed runtime was not modified for test tools.
The committed runtime-reuse guard and hosted PR Checks remain the integration gate.

## Retained limits

The complete app/all-native rebuild solely from filtered sources remains
unverified. The Lindera wheel retains its earlier publisher-build provenance;
existing dependency advisory triage remains open. macOS is ad-hoc signed and
unnotarized. Real-page OCR accuracy, native Windows interaction and new exact
installers remain unverified. Prior fresh-Mac waivers and Windows hardware gaps
retain their original scope. Source/seed verification adds no installer acceptance
or publication approval.
