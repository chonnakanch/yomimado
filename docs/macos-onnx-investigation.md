# Priority 3: ONNX inference on macOS

Investigated on 2026-10-18 against application source `6348cc0`. Production OCR,
the running development service, model files and release inputs are unchanged.

**ONNX can reduce the macOS OCR installation by about 231 MiB of regular-file
content, but the existing CPU prototype is not a good default replacement yet.**
It preserves the tested OCR outputs while decoding more slowly, reaching a
slightly higher process peak RSS, and requiring a different format for local
Marian translation imports. Keep the current Torch backend while investigating
decoder caching and Apple acceleration.

## What was tested

- Apple M5, 10 physical CPU cores, 24 GiB RAM; macOS 26.6.2 ARM64.
- Python 3.11.17, Transformers 4.57.3, NumPy 1.26.4, OpenCV 4.11.0,
  Lindera 6.0.0 and the existing pinned IPADIC resource.
- Current source path: Manga OCR 0.1.16 with Torch 2.8.0 on CPU and the
  decode-only tokenizer implemented in priorities 1/2.
- Candidate: existing exported FP32 OCR encoder/decoder, ONNX Runtime 1.22.1,
  `CPUExecutionProvider`, and the existing Torch-free detector/NMS adapter.
  No quantization, model retraining or new downloads.
- Nine existing synthetic images, including vertical text, small font, low
  contrast, skew, a mixed page and a blank image. Ten known text regions total.
- Two fresh processes per backend, three repetitions per image/process:
  **54 scans per backend, 108 scans total**. Process order is Torch → ONNX,
  then ONNX → Torch. A warmup scan precedes timed scans in every process.
- Ten additional supplied-reference crops per process check recognition without
  detector/cropping losses. No third-party manga screenshots are used.

The [benchmark](../scripts/benchmark_macos_onnx.py) reuses the existing synthetic
reference locations and scoring helpers. It records every scan, stage timings,
complete OCR responses, peak RSS, versions and fixture hashes. It does not bind
a port or call/stop the user's existing OCR service.

## Installed file size

A private ARM64 PyInstaller ONNX service was built and checked with the real
detector dependencies, including explicit `pyclipper` and `shapely.geometry`
hooks. Unused tokenizer metadata was removed consistently with the retained
Torch reference. All nine scans, Lindera offsets/base forms, JMdict and KANJIDIC2
pass in the frozen candidate; Torch/Manga OCR/UniDic/Fugashi are absent.

| Measured content              | Retained Torch runtime | ONNX candidate |
| ----------------------------- | ---------------------: | -------------: |
| Frozen Python service runtime |             465.39 MiB |     218.38 MiB |
| OCR inference weights/graphs  |             423.56 MiB |     439.41 MiB |
| Runtime plus OCR weights      |         **888.95 MiB** | **657.79 MiB** |

**Net reduction: 231.16 MiB**, about 26% of the measured runtime-plus-weights
group. The larger graphs consume 15.85 MiB of the runtime saving. Required
detector libraries are included in the final figure; a smaller preliminary
freeze omitted dynamic detector imports and is not the accepted candidate.

These are sums of regular-file bytes divided by 1,048,576, excluding symlink
aliases. Common detector code/weights, tokenizer metadata, IPADIC, learning
dictionaries, notices and native desktop UI are outside this comparison; their
unchanged bytes do not contribute to the saving. No compressed DMG/download or
complete new installer was measured.

The reference is the retained priority-1/2 Torch runtime, executable SHA-256
`6f5ccbbe8c28cff58633b520cf6d931333a7339d7aeb464ef372a92f971f2c06`.
The current-source private ONNX probe is
`8eafc8231139b77e4f602c5d7a2c054014a1be5c7283aafbbc76c16b44e256d7`.
The probe contains newer settings code and an investigation entrypoint; this is
a feasibility comparison, not two matched-source release installers.

## Speed and memory

| Local source-process measurement                          |       Torch CPU | Existing ONNX CPU prototype |
| --------------------------------------------------------- | --------------: | --------------------------: |
| Pooled median full OCR scan                               |        1,438 ms |                    1,626 ms |
| Pooled median recognition work across all crops in a scan |          185 ms |                      693 ms |
| Process peak RSS range                                    | 2,156–2,158 MiB |             2,300–2,303 MiB |
| Mixed-page scan median                                    |        5,910 ms |                    6,827 ms |

Stage medians are calculated separately and must not be summed to reconstruct
the total median. Peak RSS is the macOS process high-water mark across setup,
inference and crop checks; it is not idle memory or total desktop-app memory.
The memory observations are from the source processes, not the frozen size probe.

Timings varied substantially with process block: Torch scan medians were
789/1,489 ms, while ONNX was 1,331/1,757 ms. Background load and thermal state
were not controlled. Torch used its current four threads, ONNX used the existing
two-thread session configuration, and OpenCV used ten threads in both. These
numbers compare the implemented configurations; they do not isolate execution
engine performance or establish a reliable exact slowdown percentage.
Recognition was slower in both ONNX blocks despite that variation.

The export [explicitly disables decoder caching](../scripts/export_onnx_models.py)
with `use_cache=False`. The [current inference loop](../scripts/onnx_runtime.py)
passes the complete growing token sequence to the decoder each step. The Torch
model configuration enables caching. This identifies a concrete optimization
candidate; it does not prove that all ONNX implementations are slower.

The installed wheel reports CoreML as available, but all these measurements
explicitly select CPU. ONNX Runtime requires registering CoreML for a session;
availability alone does not establish GPU or Neural Engine execution.
[Official CoreML provider documentation](https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html).
CoreML partition coverage, fallback behavior, compile time, caching, accuracy and
speed remain unmeasured here.

## Accuracy and behavior

Both backends return **identical complete OCR responses for every fixture**,
including text, polygons, orientation, geometry source and review metadata.
Repeated outputs remain stable across both fresh processes per backend.

| Synthetic diagnostic                         | Both backends |
| -------------------------------------------- | ------------: |
| Final reference regions matched at IoU ≥ 0.5 |          9/10 |
| Full-pipeline reference strings exact        |          7/10 |
| Full-pipeline character error rate           |   7/75 = 9.3% |
| Supplied-reference crops exact               |         10/10 |
| Blank-image text                             |          None |

This preserves the current failures as well as successes. It does not establish
real-manga accuracy, better detection or performance on other Mac hardware.
First-pass/final geometry scores and every case are retained in the evidence.

## Translation compatibility

Removing Torch affects more than OCR. The current macOS importer accepts Marian
Torch/Safetensors folders; an ONNX-only runtime cannot load those weights.
It would need compatible `model/` plus `onnx/` exports, as the current Windows
path does. Existing imported records identify their backend and cannot silently
be reused as ONNX models. Original files must be preserved, with an explicit
migration or a separately installed Torch runtime if that format is retained.

Local Ollama translation uses its own process and is independent of these OCR
engines. Keeping Torch bundled for Marian imports would retain most of the
dependency this investigation is trying to remove. No provider/import behavior
is changed by this investigation.

## Recommendation and required work

Keep the existing macOS backend as default. Investigate a cached ONNX decoder
and a separate CoreML profile next, retaining exact output/geometry checks.
Decide how to preserve or migrate user-installed Torch translation models before
removing their runtime. The size benefit is concrete; a speed or memory benefit
has not been demonstrated.

A production migration would reuse the detector/recognizer factory boundary and
the existing translation provider boundary. It would also require a macOS frozen
entrypoint, graph/resource verification, native launch configuration, import
migration behavior, updated dependency/source/notices, a fresh reviewed runtime
seed and exact installer acceptance. Windows-only startup guards stay in place.
The existing macOS seed-reuse guard was not relaxed. Nothing is published or
approved for publication.

ONNX Runtime 1.22.1's macOS wheel carries MIT and third-party notices. The private
freeze retains both original files. [Exact wheel/native/notice/model hashes](macos-onnx-investigation-inputs.json)
record this experiment; they are not a production dependency lock or release
approval. Existing detector/model licensing obligations remain applicable.

## Reproduce and evidence

With the already prepared local environments, pinned exports and synthetic
fixtures used earlier in this branch:

```sh
rtk services/ocr/build/release-venv/bin/python scripts/benchmark_macos_onnx.py \
  --fixtures services/ocr/build/lindera-experiment-20261017/scan-benchmark \
  --exports services/ocr/build/resource-reduction-20261018/onnx-export \
  --output services/ocr/build/macos-onnx-investigation-20261018 \
  --rounds 2 --repeats 3
```

The ignored output directory contains four source-process reports,
`comparison.json`, exact `measured-benchmark-source.py`, the private PyInstaller
recipe/entrypoint/log, `frozen-smoke.json` and `frozen-size.json`. The last file
records every final runtime file's size/hash and retained license hashes. No
model files or fixture images are committed. The measured source hash is
`ae3104f5c2cd973464c7de4bbd0450811629cbe11fc51407402d4aefb524ac8e`;
the current script only moves the macOS-specific `resource` import into its
worker so metric tests can import on Windows.

Three new metric checks cover inserted text outside reference regions, blank
images without a character-accuracy denominator, and cross-process fixture
mismatches. Existing geometry, Unicode edit-distance and ONNX graph-input tests
remain applicable. Frozen OCR/learning smoke passes; CoreML, native Windows and
exact new installers are outside this experiment's acceptance scope.
