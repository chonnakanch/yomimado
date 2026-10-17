# Scan speed and accuracy: Sudachi versus Lindera

Measured on 2026-10-17 on the local macOS ARM64 development environment, using
source `4912558` and the recorded benchmark/input hashes.

**Changing the learning tokenizer does not improve text detection or OCR in
this experiment.** Both profiles use the same detector and Manga OCR models.
All 90 scans returned identical text, polygons, orientations and review metadata
for the corresponding image. Lindera reduces dictionary size; its development
adapter is slower at tokenization here, although that cost is below a millisecond.

## Speed

Nine synthetic images, five repetitions per image/profile, alternating profile
order. Models and both tokenizers are loaded before timed scans, with an OCR
warmup. Times are local service function calls, excluding native screen capture,
HTTP/IPC, window rendering, dictionary lookup and translation. Tokenization is
measured separately as if the user opened every returned region.

| Median across the balanced image set     | Sudachi Core | Lindera + IPADIC |
| ---------------------------------------- | -----------: | ---------------: |
| OCR scan, detector through final regions |       836 ms |           840 ms |
| Detector adapter work, all passes        |       734 ms |           725 ms |
| Manga OCR recognition work, all crops    |       126 ms |           125 ms |
| Analyze all returned regions             |     0.063 ms |         0.169 ms |

Stage medians are computed separately and should not be added to reproduce the
scan median. Both profiles share unchanged OCR implementations and model
instances to isolate tokenizer behavior. The few-millisecond scan differences
are run variation, not a detector improvement attributable to either tokenizer.
This does not compare separate-process memory pressure or controlled cold starts.

| Image                      | Dimensions | Detector passes per scan | Sudachi scan median | Lindera scan median |
| -------------------------- | ---------- | -----------------------: | ------------------: | ------------------: |
| Small horizontal selection | 240 × 100  |                        1 |              820 ms |              825 ms |
| Small vertical selection   | 100 × 240  |                        1 |              839 ms |              854 ms |
| Horizontal sentence        | 640 × 140  |                        1 |              816 ms |              824 ms |
| Vertical sentence          | 140 × 600  |                        1 |              820 ms |              818 ms |
| Small font                 | 600 × 140  |                        1 |              836 ms |              825 ms |
| Low contrast               | 640 × 140  |                        1 |              967 ms |              963 ms |
| Three-degree skew          | 640 × 160  |                        1 |              875 ms |              876 ms |
| Three-region mixed page    | 960 × 1100 |                        5 |            4,373 ms |            4,528 ms |
| Blank image                | 600 × 600  |                        1 |              825 ms |              830 ms |

The mixed page triggers a full-image detector pass plus four tile passes through
the existing bounded retry path. Detector time there is approximately
4.02–4.18 seconds, while recognition is about 0.33 seconds. Retry policy and
detector execution are the main speed targets supported by this run. The blank
image still invokes the detector, even though it produces no recognition work.

Model construction and Manga OCR's built-in warmup took about 1.57 seconds once,
outside timed samples. This is not a complete app cold-start measurement.
The process used the library defaults: four Torch threads and ten OpenCV threads.
No GPU or thread tuning was applied. Background system activity was not controlled.

## Accuracy

The generated data has **10 known text regions across nine images**, including
one blank image. Both profiles produce the same OCR results, so the following
OCR metrics apply equally to both. This is a diagnostic for these fonts/layouts,
not a measured real-manga accuracy rate.

| Measurement                                                        | Result for both profiles                                |
| ------------------------------------------------------------------ | ------------------------------------------------------- |
| First full-image detector pass, strict box matching                | 7/10 reference regions matched; 5 unmatched predictions |
| Final regions after retries/geometry recovery, strict box matching | 9/10 matched; 2 unmatched predictions                   |
| Final matched region orientation                                   | 8/9 correct                                             |
| Full-pipeline text, aligned to known synthetic locations           | 7/10 reference strings exact                            |
| Full-pipeline character error rate                                 | 7 edits / 75 reference characters = **9.3% CER**        |
| Recognition on supplied ground-truth crops                         | 10/10 strings exact; **0% CER**                         |
| Blank-image false text                                             | None                                                    |

Box matching uses axis-aligned bounds and IoU ≥ 0.5 with one-to-one matching.
First-pass precision/recall are 58.3%/70%; final-region precision/recall are
81.8%/90%. An unmatched prediction can be a split or incomplete text region;
it does not necessarily mean text was hallucinated on empty artwork. These
geometry metrics must not be interpreted as character recognition accuracy.

Full-pipeline text is aligned by overlap with the known generated locations.
Split predictions assigned to the same reference are sorted along that known
region's direction and concatenated. Missing characters count as deletions;
predictions outside all reference locations count as insertions. Only whitespace
is removed for text comparison. This is benchmark alignment with supplied layout,
not new automatic reading-order behavior in the app.

The supplied-crop test bypasses detection and measures Manga OCR on each true
text crop with eight pixels of surrounding context. Its perfect result here
does **not** mean the app has perfect OCR. Actual pipeline losses were:

- Both small `学校へ` samples returned `学校`, losing `へ`. The short vertical
  region was also classified as horizontal.
- The low-contrast `お兄ちゃん、待って！` sample returned two regions that combine
  to `兄ちゃん、は`, with five character edits.
- The remaining seven reference strings were exact, including all three mixed-page
  regions. These failures are shared by both tokenizers and point toward region
  detection/cropping/fallback behavior as a useful next investigation.

Tokenization quality remains a separate measure. The eight focused
word/reading/base-form compatibility checks give **8/8 for Sudachi** and
**7/8 for Lindera**, whose `お兄ちゃん` result is split. These are hand-selected
checks, not general language accuracy percentages. See the broader
[39-sentence tokenizer comparison](lindera-tokenizer-experiment.md).

## Reproduce and inspect

The [benchmark](../scripts/benchmark_scan_pipeline.py) configures existing local
resources through the corrected development launcher. It downloads nothing and
does not connect to or stop the user's running service.

```sh
rtk services/ocr/build/release-venv/bin/python scripts/benchmark_scan_pipeline.py \
  --font '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc' \
  --output services/ocr/build/lindera-experiment-20261017/scan-benchmark \
  --repeats 5
```

The ignored output directory contains generated PNG fixtures, every timing sample,
OCR regions, ground truth, accuracy cases and `comparison.json`. The report
retains versions and SHA-256 values for the detector, recognition weights, font
and measured benchmark source. The detector wrapper times preprocessing,
inference and detector postprocessing together; it does not instrument individual
OpenCV network operators.

For this recorded run, full-pipeline text metrics were derived afterward from
the already captured regions, without rerunning inference. The original timing
report and exact measured script are preserved as `comparison-measured.json`
and `measured-benchmark-source.py`; `derivedMetricAnalysisSha256` identifies the
analysis revision. The current benchmark calculates these text metrics directly
on future runs.

The environment uses Python 3.11.17, Torch 2.8.0, Transformers 4.57.3, NumPy 1.26.4,
Pillow 11.3.0, Lindera 6.0.0 and SudachiPy 0.6.10/Core 20250515. Native Windows,
frozen services, interactive screen-to-overlay latency and real manga accuracy
were not tested. No production OCR behavior, dependency lock, runtime seed or
installer is changed by this benchmark.

Seven [metric tests](../scripts/tests/test_scan_benchmark_metrics.py) cover IoU,
duplicate/missing detections, orientation errors, Unicode edit distance, missing
text, split predictions and unmatched inserted text. Python lint/format and
documentation checks pass. Existing source and installer evidence is preserved.
