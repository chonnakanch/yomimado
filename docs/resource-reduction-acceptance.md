# Resource reduction: private packaging and real-page checks

Verified on **2026-10-18** on the development Apple Silicon Mac (Apple M5,
24 GiB RAM, macOS 26.6.2). Candidate source:
`907636e25f361432606e92b752a738f35d9bc1a7`.
This is a private, ad-hoc signed, unnotarized test build. It does not approve a
runtime seed, corresponding-source delivery or public installer.

## Actual packaged size

| Measurement                             | Retained 0.2.0 private build | Resource-reduction private build |             Saving |
| --------------------------------------- | ---------------------------: | -------------------------------: | -----------------: |
| Compressed DMG                          |                   999.39 MiB |                       625.63 MiB | 373.76 MiB (37.4%) |
| Copied app file content                 |                 1,907.15 MiB |                     1,205.22 MiB | 701.93 MiB (36.8%) |
| Copied app allocation on this APFS host |                 1,918.63 MiB |                     1,221.64 MiB |         697.00 MiB |
| Packaged Python runtime file content    |                 1,152.71 MiB |                       697.13 MiB |         455.58 MiB |
| Assets file content                     |                   727.59 MiB |                       480.73 MiB |         246.86 MiB |

File content sums regular files and excludes symbolic links. Allocation is
`du -sk`; it depends on the destination filesystem. App measurements are from
apps copied/mounted from their exact disk images, rather than just PyInstaller's
output. These are different source/version builds, not a controlled attribution
of each byte saved. The baseline is the retained **private** `fae4d28` test DMG,
SHA-256 `e804cce042c16e3eb1a392861e4c3a75e9f2acb9b7df557794b20e66c0afef02`;
it is not a published installer or the later approved-source seed DMG.

New DMG SHA-256:
`7fb480db4b350bb2744de4050c2614217a1a410c51f02e9e904e9641de4b9360`.
The preserved private file is
`services/ocr/build/resource-acceptance-20261018/candidate/YomiMado_0.2.2_resource-test_907636e_aarch64.dmg`.

The new installer contains neither translation weights nor detector weights.
Lindera/IPADIC, Manga OCR recognition weights, JMdict and KANJIDIC2 remain local.
macOS continues to use Torch; the experimental ONNX/CoreML profiles are not used.

## Packaging failure found and fixed

The first fresh build failed the existing bundle verifier: Transformers'
PyInstaller hook copied `SudachiPy` and `sudachidict_core` distribution metadata
from the development environment, despite the excluded modules/dictionary.
The shared metadata cleanup now removes these obsolete records as well as
UniDic/Fugashi metadata. A regression verifies that cleanup preserves Lindera
metadata and leaves accidentally collected old code in place for the verifier
to reject. It does not weaken the existing bundle gate.

All **265 release-tool tests** and changed-script Ruff checks pass.
CI's model-free service selection also includes the three component/packaging
tests, bringing that selection to **187 passing tests without skips**. The frontend
production build and native macOS release build pass. The rebuilt exact DMG
passes mounted bundle, ARM64/deployment-target and native-library-link checks.
Its copied app passes the resource-seal check and every native code-signature
check. All **29 frozen application modules** match their current source;
the source-only Sudachi adapter is absent.

Native input comparison against the retained pre-feature resources finds 112
unique inputs instead of 114: Lindera is added, Fugashi/libmecab and Sudachi's
binding are removed, and all shared input hashes remain unchanged. This records
technical identity, without extending the old native/source approval to Lindera.

## Packaged behavior

The exact DMG app was copied into an isolated test folder, leaving the user's
installed app intact. Its frozen service runs with fresh databases, an empty
translation-model location and no external `PYTHONPATH` or tokenizer overrides.
Checks pass for:

- Real-page OCR and a uniform blank capture, retaining complete source responses.
- Lindera readings, dictionary forms and Unicode code-point spans after an emoji.
- JMdict word lookup and KANJIDIC2 meanings/readings.
- Initial translation provider `none`, model state `notInstalled`, and HTTP 503
  when translation is requested before setup.
- Explicit import of a verified local Marian fixture, on-demand translation,
  saved words/sentences and translation-cache persistence across service restart.

The native app also launches with an isolated home directory, creates fresh app
data and automatically starts the bundled backend. Its actual Settings → Reading
page shows **“No translation model installed. Import a model or install one
through Ollama to get started.”** Quit stops both the test app and its service.
Ollama itself was left to the owner as requested.

This does not establish Finder/quarantine acceptance, Screen Recording permission,
live capture/overlay alignment or physical Retina/mixed-DPI behavior for this hash.

## Real manga screenshot comparison

The owner selected one local screenshot. Its images, manually transcribed text,
raw OCR responses and benchmark remain under the ignored build directory. They
are not included in Git or uploaded as fixtures. The public
[aggregate evidence](resource-reduction-acceptance-results.json) contains hashes,
sizes, counts and timings without the screenshot, transcriptions or private
input path.

The screenshot contains vertical dialogue, furigana, small text and dense artwork.
Six inputs cover the manga area at original size, a 67% resized copy, a contrast
factor 0.35 copy, and three overlapping crops. These are **one real screenshot
and its variants**, not six independent manga pages. Crop coordinates and pixel
generation are retained in the private measured script.

Baseline `7cf0154` and the current pipeline share warmed Torch/OpenCV models.
Two scans per profile/input alternate their order: **24 measured source scans**.
Every repeated response is stable, and all six complete optimized outputs equal
the baseline, including text, geometry, orientation and other response fields.
The copied app's frozen service separately reproduces all six complete outputs.

| Input                     | Baseline warm median | Optimized warm median | Detector passes, both |
| ------------------------- | -------------------: | --------------------: | --------------------: |
| Original manga area       |               3.15 s |                3.15 s |                     1 |
| 67% size                  |               7.25 s |                7.43 s |                     7 |
| Lower contrast            |               3.38 s |                3.32 s |                     1 |
| Small-kana dialogue crop  |               0.98 s |                1.00 s |                     1 |
| Dense-art panel crop      |               4.31 s |                4.32 s |                     5 |
| Small-dialogue panel crop |               3.47 s |                3.40 s |                     4 |

These few warm repetitions do not establish a speed regression or improvement.
No detector passes or recognition calls are eliminated on these content-bearing
inputs. The sparse/uniform-image speedups in the
[earlier benchmark](detector-retry-optimization.md) should not be generalized to
dense pages. Frozen HTTP timings include different startup/request conditions
and are not compared with this warmed in-process table.

For a manually annotated subset of 22 dialogue/narration regions, the original
page matches 12/22 raw strings (14.56% character error rate). A secondary score
applies NFKC and removes Unicode punctuation/whitespace while retaining kana:
**20/22 match, 12 edits over 195 reference characters (6.15%)**. The smaller copy
matches 19/22 under that policy; the lower-contrast copy matches 17/22. Manual
recognizer crops match 14/22 raw and 21/22 normalized strings. Width, ellipsis and
dash conventions account for many raw-string differences.

Accuracy uses reference-box overlap to associate outputs with the annotated
subset. Furigana/decorative sound effects are not reference targets; unmatched
outputs are retained privately and excluded from this subset error rate. Connected
bubbles can merge into one region, so assignment counts the lost boundary and
misassociated text separately. This is a diagnostic subset score, not calibrated
page-wide detection precision/recall or a general Manga OCR accuracy estimate.

Existing failures remain: connected bubbles merge, low contrast can duplicate
overlapping detections, and a tight small-kana crop fragments text that works in
the full page. Both pipelines have the same failures. None warrants discarding
content-bearing recovery tiles or claiming an accuracy improvement in this branch.

## Remaining work

- **Native Windows installer verification is still pending.** This host is
  macOS. The previous hosted Checks success covers native debug builds/tests,
  not a newly frozen Windows installer. Private seed access remains protected
  on `main`; no release workflow or approval guard was changed to bypass it.
- **New runtime/source review remains open.** Exact Lindera native dependency
  delivery and IPADIC source-to-binary provenance need completion, as recorded
  in the [Lindera notice](../THIRD_PARTY_LICENSES/lindera/README.md). No refreshed
  CI seed was approved, uploaded or activated.
- Exact future installer acceptance and any public release still require the
  separate owner-authorized release process. Earlier installer evidence remains
  tied to its original hashes.
- A further size opportunity is now measured: Tauri materializes eight native
  library aliases as identical regular files, adding **242,969,200 bytes
  (231.71 MiB)** to the copied app. Preserving valid runtime links would need a
  separate packaging/signature/native-load check. No aliases were modified here.

Local evidence is retained under
`services/ocr/build/resource-acceptance-20261018/`: the exact candidate and
checksum, rejected first bundle, build/verification logs, isolated copied app,
source-bytecode report, native-input comparison, size report, private page
fixtures/results and frozen/import/restart/UI records.
