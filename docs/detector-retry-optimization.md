# Priority 4: avoid unnecessary detection and crop work

Implemented on 2026-10-18 against `7cf0154`, retaining the existing Torch OCR
backend on macOS and ONNX OCR backend on Windows. Detector model, input size,
thresholds, tile geometry/limit, mask recovery, stroke expansion and coordinate
handling are unchanged. No model or dependency bundle is added or removed.

## Implemented behavior

- A capture that is exactly one RGB color returns an empty OCR response before
  loading/invoking the models. PNG dimension and configured-resource validation
  still run. Debug mode returns an empty detection list and zero retry counts.
- Exactly uniform retry tiles are omitted. Any pixel variation in any RGB
  channel, even one level, keeps the existing detection/recovery path. This uses
  no darkness/contrast threshold, text confidence heuristic or grayscale-only
  assumption. The existing nearly uniform **recognition-crop** filter is unchanged.
- Recognition results for identical image-space crop bounds are reused within
  one scan. Different bounds are independent even when their pixels match.
  Nothing is reused across scans; failed calls are not cached. Geometry,
  duplicate-region decisions, review metadata and selection fallback remain
  governed by the existing pipeline.

The change is confined to the [Python pipeline](../services/ocr/app/pipeline/real_ocr.py).
Debug tile/mask retry counts reflect the nonuniform tiles actually attempted.
The native capture/overlay path and frontend API contract are unchanged.

## Measured scan times

Apple M5 / 24 GiB RAM / macOS 26.6.2 ARM64, Python 3.11.17, Torch 2.8.0,
OpenCV 4.11.0, Transformers 4.57.3. Four Torch threads and the existing OpenCV
GCD configuration (reported ten threads); no thread configuration change shipped.

The [benchmark](../scripts/benchmark_detector_retries.py) loads the baseline
pipeline directly from Git, shares warmed model instances with the candidate,
and alternates profile order. Two repetitions of 13 synthetic images per
profile, three profiles: **78 measured scans** (26 each). The nine original
fixtures are reused byte-for-byte. Added fixtures are three sparse pages with
14/24/40-pixel Japanese text and one large uniform image. No manga screenshots,
downloads or running-service requests are involved.

| Fixture                    | Baseline median | Optimized median | Detector passes before → after |
| -------------------------- | --------------: | ---------------: | -----------------------------: |
| Uniform 600 × 600          |          922 ms |           5.9 ms |                          1 → 0 |
| Uniform 960 × 1100         |        5,826 ms |          24.4 ms |                          5 → 0 |
| Sparse page, 14-pixel text |        4,750 ms |         2,013 ms |                          5 → 2 |
| Sparse page, 24-pixel text |        4,914 ms |         2,005 ms |                          5 → 2 |
| Sparse page, 40-pixel text |        5,488 ms |         2,207 ms |                          5 → 2 |
| Three-region mixed page    |        4,890 ms |         4,848 ms |                          5 → 5 |

These gains apply to flat areas and sparse pages. The mixed page retains all
its passes; its small timing difference is run variation. Pooled scan medians
are 1,048/1,001 ms for baseline/candidate, but the artificial fixture mix is not
a representative user workload. Two samples per fixture/profile, shared models,
uncontrolled background load and thermal state limit timing conclusions. These
are service function timings, excluding capture, HTTP/IPC and overlay rendering.

The detector's blob-construction/network-forward wrapper accounts for **99.52%**
of summed baseline detector time; refined-mask postprocessing accounts for
**0.13%**. Removing that refinement alone would address very little measured
work. This instrumentation does not isolate individual OpenCV operators.

The benchmark's fixtures did not exercise recognition-cache hits: recognition
call counts stay the same for baseline/candidate. Crop reuse is separately
verified with duplicate bounds and identical whole-selection fallback tests;
no measured recognition speedup is attributed to it here.

## Accuracy and retry policy

All 26 optimized scans preserve the baseline's **complete OCR responses** for
their matching images, including text, polygons, orientation and review flags.
The original nine-fixture failures remain: 7/10 reference strings exact and
7/75 character edits. With the three sparse-page strings, both profiles give
10/13 exact and 7/84 edits (8.3% CER). Uniform images produce no false text.
These are synthetic diagnostics, not general manga accuracy rates.

A third benchmark profile disables **all** tile passes. It also preserves the
outputs in this small set and reduces the mixed page to about 1,247 ms. That
does not establish safety for manga. Existing recovery tests explicitly exercise
full-pass omissions that tiles and segmentation masks recover, including short
vertical Japanese. **The all-tiles-disabled profile is not shipped.** More
representative user-local fixtures are needed to justify broader retry pruning.

Eight new service checks cover uniform colors, missing-resource errors,
single-level pixel variation, equal-luminance colored content, tile selection,
crop bounds, request isolation and selection fallback reuse. Existing tile,
mask, short-vertical recovery and geometry checks continue to pass. Two existing
test fixtures now contain variation outside the crop under test, preserving
their intended eight-pass and recognition-crop-filter coverage.

All **169 service tests**, **264 research/release-tool tests**, Ruff and changed
documentation formatting pass. A separate Torch-free ONNX CPU source run on
macOS preserves all nine original OCR outputs and loads none of the blocked
Torch/Manga OCR/UniDic/Fugashi modules. It is not native Windows acceptance.
No frontend/native code or API shape changed, so no native installer was built.
Future packaging still needs the appropriate source/notices/runtime review and
new installer acceptance. Historical installer evidence is unchanged.

## Reproduce and evidence

With the existing local model/development environments:

```sh
rtk services/ocr/build/release-venv/bin/python scripts/benchmark_detector_retries.py \
  --baseline-ref 7cf0154 --repeats 2 \
  --output services/ocr/build/detector-priority4-20261018
```

[Recorded metrics and hashes](detector-retry-optimization-results.json) include
every fixture's timings, call counts, geometry/text scores, verified model inputs
and source identities. Input hashes were verified again after timing. The ignored
output directory retains all samples, complete responses, baseline/current
source snapshots, generated fixtures and the ONNX smoke result. The benchmark
also retains the all-tiles-disabled ablation; it does not configure the app to
use it. Restart the development OCR service to load the updated pipeline.
