# Priority 3 follow-up: decoder cache and CoreML

Investigated on 2026-10-18 from application source `df92bb0`, on the same Apple
M5 / 24 GiB / macOS 26.6.2 ARM64 machine as the
[first ONNX study](macos-onnx-investigation.md). The production factory, running
development service, translation selection, dependency locks and runtime seed
are unchanged. All exports and measurements use local pinned assets.

**Caching improves the ONNX CPU recognizer, but does not close its gap with
Torch in this experiment. CoreML accelerates recognition but its memory, startup
and generated-cache costs make this profile unsuitable for the size-reduction
default.** Keep the current macOS backend while treating cached CPU ONNX as an
optional migration candidate that needs frozen verification and translation
compatibility work.

## Full scan comparison

Two fresh processes per profile, three repetitions of nine synthetic images per
process: **54 scans per profile, 216 scans total**. Process order is Torch →
full-prefix CPU ONNX → cached CPU ONNX → CoreML encoder/cached CPU decoder,
then the reverse order. Each process warms up before timed scans. Profiling is
disabled for timing runs; separate diagnostic runs verify execution placement.

| Source-process measurement              |       Torch CPU | Full-prefix ONNX CPU | Cached ONNX CPU | CoreML encoder + cached CPU decoder |
| --------------------------------------- | --------------: | -------------------: | --------------: | ----------------------------------: |
| Pooled median full scan                 |        1,430 ms |             1,814 ms |        1,588 ms |                            1,373 ms |
| Pooled median recognition work per scan |          196 ms |               692 ms |          396 ms |                              153 ms |
| Process peak RSS                        | 2,155–2,158 MiB |      2,299–2,301 MiB | 2,348–2,353 MiB |                           5,374 MiB |

All profiles return **identical complete OCR responses on every image and
repetition**, including text, polygons, orientation and review metadata.
Reference crops are 10/10 exact; the unchanged full pipeline matches 9/10
reference regions, gives 7/10 exact reference strings and 7/75 character edits
(9.3% CER). No blank-image text appears. These are synthetic diagnostics, not
a claim about general manga accuracy.

The CPU recognition improvement appears in both blocks: full-prefix/cached
medians are 646/320 ms and 851/397 ms. Torch recognition medians vary from
125 to 235 ms; CoreML stays near 149/154 ms. CoreML is slower than Torch in the
first block and faster in the second. The small pooled full-scan advantage does
not establish a reliable general speedup over Torch.

Detection dominates most scan time and its block medians drift despite the
unchanged detector. Background load and thermal state were not controlled.
Torch uses its current four threads, ORT two intra-op/one inter-op threads, and
OpenCV ten threads. Stage medians are separate statistics and must not be
summed. Peak RSS covers source-process setup and inference, not idle memory,
the whole desktop app or a new frozen runtime.

CoreML encoder session creation with an existing compiled cache still takes
17.12–17.67 seconds across the scan processes; the first successful diagnostic
setup takes 86.34 seconds. CPU cached decoder/encoder sessions together take
about 0.24–0.26 seconds, excluding shared detector/setup work. The harness's
generic import/through-ready fields omit earlier verification and candidate
module imports; they are not complete end-user startup comparisons.

[Recorded values and exact input/evidence hashes](macos-onnx-cache-coreml-results.json)
retain both blocks, complete profile metadata and model sizes.

## Cached decoder

The private [exporter](../scripts/export_cached_ocr.py) creates a one-token
prefill graph and a single-token decoder with past key/value tensors for both
self attention and cross attention. The existing image encoder is reused.
Both decoder graphs reference one shared external weights file; the prefill
graph does not duplicate the model's weights on disk.

The [experimental adapter](../scripts/onnx_cached_experiment.py) retains the
existing NumPy generation policy, tokenizer, image preparation and text cleanup.
For every generation step it matches selected beam prefixes to their previous
parents and reorders all eight cache tensors. Duplicate identical prefixes can
reuse the same deterministic evaluation cache. Cache state belongs to one crop;
it is never shared between images or requests.

The exported graphs pass ONNX checking. Cached CPU inference passes all ten
reference crops. A separate numerical check compares full-prefix and cached
next-token logits at lengths 1–24, with one and four beams, including duplicate
and reordered parents: all 48 comparisons pass, with maximum absolute difference
`0.000006676`. These checks address the exporter's trace warnings for dynamic
cache lengths; they do not prove every possible input/generation length.

The new decoder files total **117,522,004 bytes**, compared with 117,428,711
bytes for the old full-prefix decoder: **93,293 additional bytes** (0.089 MiB).
This is model-file content only. Two sessions can still hold separate weight
copies in memory; shared external storage does not prove shared RAM. No new
frozen-runtime or compressed-installer saving is claimed.

## CoreML behavior

Sessions explicitly request ONNX Runtime 1.22.1's CoreML execution provider with
`MLProgram`, `MLComputeUnits=ALL`, dynamic inputs allowed and CPU fallback for
unsupported operations. A content-based cache directory is confined to the
ignored experiment output. Cached decoder keys include the external weights
hash as well as the graph hash. No provider or model download is performed.

CoreML's image encoder passes all ten reference crops. ONNX Runtime profiling
records ten CoreML encoder partition calls and no CPU encoder kernel calls;
the decoder in this profile explicitly runs on CPU. This proves provider
delegation, not which Apple compute unit executed each operation. `ALL` allows
CoreML to choose supported hardware; it does not establish Neural Engine use.

The initial sandboxed attempt failed because Apple's compiler could not create
its working directory. Retrying with local compiler/hardware access succeeded.
The first successful encoder session creation took **86.34 seconds**; the diagnostic process
reached **5,225 MiB peak RSS** across setup and ten crop checks. Warm cached
session loading is measured separately in the scan comparison.
This retry is not a pristine machine-cache cold-start measurement.

The successful encoder's generated cache contains **1,658,536,336 regular-file
bytes** (1.545 GiB; 1,660,215,296 allocated bytes on this filesystem). This
includes the CoreML source and compiled artifacts retained by this ORT version,
excluding diagnostic profiles and failed decoder artifacts. That additional
disk content is much larger than the first study's 231 MiB runtime-plus-weights
saving. A small distributable runtime alone would not make this CoreML setup a
smaller installation after use.

Requesting CoreML for the cached decoder fails during model initialization.
ORT reports 21 candidate partitions covering 66 of 196 graph nodes, then CoreML
rejects unbounded dimensions and a matmul shape while building its execution
plan (error `-14`). There is no successful all-CoreML OCR profile. The failure
is retained as a failure, rather than a silently retried CPU timing result.

Provider configuration and caching behavior follow the
[official CoreML provider documentation](https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html).
These results apply to this exact model export, runtime version and machine;
they do not establish that every CoreML decoder or newer runtime will fail.

## Scope and release implications

No detector graph, threshold, preprocessing, crop retry, geometry handling,
Lindera resource or learning dictionary is changed. A recognizer optimization
does not directly accelerate the current OpenCV text detector.

Removing Torch still requires a decision about existing user-imported Marian
Torch models. Ollama runs independently. The earlier frozen-runtime feasibility
measurement is not a frozen verification of this new cached adapter; a matched
freeze and fresh source/notices/seed review remain necessary before production
integration. No installer has been published or approved.

## Reproduce

Use the existing pinned local Torch export environment, ONNX environment and
Torch-free dependency overlay described in the first investigation. With the
ONNX environment's `onnx` package available to the Torch interpreter:

```sh
rtk env PYTHONPATH=services/ocr/build/onnx-prototype/venv/lib/python3.11/site-packages \
  services/ocr/build/release-venv/bin/python scripts/export_cached_ocr.py \
  --model apps/desktop/src-tauri/resources/ocr/assets/manga-ocr-base \
  --output services/ocr/build/macos-onnx-cached-coreml-20261018/cached-final

rtk services/ocr/build/release-venv/bin/python scripts/benchmark_cached_coreml.py \
  --cached services/ocr/build/macos-onnx-cached-coreml-20261018/cached-final
```

The exporter refuses to overwrite an existing output directory. Use a new
directory for a new export and pass it with `--cached`. The benchmark runs
bounded, sequential child processes without binding a service port. CoreML
requires access to Apple's local compiler/hardware outside the restricted
execution sandbox. `--variant NAME --diagnostic --result PATH` runs the separate
profile/crop check with the prepared Torch-free environment. Diagnostic results
include profiling overhead and must not be treated as warm scan timings.

The ignored experiment directory retains every source-process report, complete
OCR outputs, diagnostic profiles, graph/weights hashes, compiled CoreML cache
and failure evidence. Five model-independent checks cover beam duplication,
reordering, all cache tensor slots, missing parents and invalid prompt lengths.
