# Windows ONNX feasibility experiment

Implemented 2026-10-10 following the maintainer's choice to avoid long Torch
source builds. This is an isolated backend experiment: the existing Windows
installer, shared service and macOS runtime remain unchanged. No public release,
native-source clearance or human installer approval is granted.

## What is implemented

- Hash-check the original recognition/translation model files against
  `services/ocr/windows-assets.json`, then export four opset-17 encoder/decoder
  graphs using **prebuilt** Torch 2.8.0 and Transformers 4.57.3. Export is model
  conversion, not a Torch compiler build. ONNX 1.18.0 is export-only.
- Infer using prebuilt CPU ONNX Runtime 1.22.1 and NumPy. Generation preserves
  the pinned Manga OCR four-beam/three-token repetition policy and Marian
  six-beam/blocked-padding/forced-EOS policy. It uses full decoder prefixes;
  cache optimization is deferred until behavior is demonstrated.
- Adapt only the exact pinned detector's CPU inference postprocessing. Original
  segmentation/grouping/mask refinement and `TextDetector.__call__` are retained;
  NumPy replaces Torch/torchvision NMS. Training/PyTorch loaders are excluded.
  This remains GPL-derived detector code, with original source, licence and
  explicit adaptation recipe preserved. It continues to use OpenCV DNN, so
  the original IPP issue is not resolved by this prototype alone.
- Compare the complete existing OCR pipeline on synthetic horizontal/vertical
  fixtures in separate baseline and ONNX processes. Compare three freshly
  generated translations and SQLite cache reuse after service recreation.
  The ONNX child denies actual Torch imports; Windows uses a separate environment
  that physically excludes Torch, torchvision, Manga OCR and torchsummary.
- Record graph/model hashes, runtime versions, timings and Windows actual loaded
  module hashes. Check added Windows native wheel members are AMD64.

The detector ONNX weights remain a separate smoke-only user-installed input.
They are not exported, committed, copied into release resources or uploaded.
All evidence artifact paths accept only textual JSON/log files. No manga artwork
is used; the Manga OCR warm-up image is replaced by a synthetic white image.

## Local result

The development Mac's source-built Python 3.11.17 environment and prebuilt
ONNX Runtime 1.22.1 pass **exact response equality** for both synthetic OCR
fixtures, including text, polygons, orientation and confidence. Three uncached
translations match the existing provider exactly:

1. `今日は学校に行きます。`
2. `この本は面白いです。`
3. `無理のしすぎはダメだよ。`

The ONNX child imports no Torch/torchvision. The comparison retains baseline
and ONNX reports in ignored `services/ocr/build/onnx-prototype/comparison/`.
These are bounded fixtures, not a claim of identical output for every page or
sentence. Beam candidate ties and floating-point differences remain parity risks.

Illustrative initial timings on this Mac: baseline OCR 2.21/0.77 seconds and
ONNX OCR 1.41/0.93 seconds for horizontal/vertical fixtures. The three short
translations took 0.07–0.27 seconds in the baseline and 0.30–0.46 seconds in
the full-prefix ONNX prototype. These include first-use costs inconsistently
between operations and are observations, not a controlled benchmark or Windows
speed claim. Long sentences/page workloads and memory use still need testing.

Eleven focused tests cover class-aware suppression, strict confidence/IoU
thresholds, the output cap, input preservation, repetition/banned tokens,
forced EOS, completed-beam ranking, artifact exclusion and 20 randomized NMS
comparisons with the actual torchvision CPU operator.

## Windows execution

**Windows ONNX feasibility** runs on `develop` when its exact prototype inputs
change. It has a 40-minute cap, read-only repository access and no native compiler,
freezer, installer or publisher. It uses the hosted Windows x64 Python 3.11.9
bootstrap; this explicitly does not establish final frozen Python 3.11.17 coverage.
It prepares exact existing baseline inputs and separately pinned ONNX inputs,
exports the original models, then performs the offline comparison without Torch
in the runtime environment. The evidence artifact is
`windows-onnx-feasibility-evidence`.

A successful hosted result must precede any selection of this backend for
Windows packaging. Manual dispatch on a non-default branch may not have a Run
button until GitHub registers the workflow; its constrained push trigger avoids
requiring changes to `main`.

## Exact dependency review scope

`scripts/onnx-probe-inputs.json` binds seven exact official PyPI wheels to SHA-256,
native members and embedded notices. Original licence bytes are retained under
`THIRD_PARTY_LICENSES/windows-onnx-probe/`. Export-only packages are ONNX 1.18.0
and ml_dtypes 0.5.1. Runtime additions are ONNX Runtime 1.22.1, flatbuffers
25.2.10, coloredlogs 15.0.1, humanfriendly 10.0 and the Windows-only console helper
pyreadline3 3.5.4. The latter's package licence explicitly allows file-specific
terms, which still require review before final redistribution.

ONNX Runtime's top-level licence is MIT, but its wheel carries a broad
`ThirdPartyNotices.txt`, including restrictive MKL terms. A shared notice is not
proof that this CPU wheel includes MKL, nor proof that it does not. Exact native
dependency/build/source review remains open. The prototype never marks these
inputs publicly approved. ml_dtypes/Eigen and other embedded source notices also
remain separate from the top-level package label.

The final Windows runtime must resolve OpenCV/IPP, NumPy/BLAS, geometry libraries,
codecs, Python/compiler runtime, installer and every other remaining item in
[the source worksheet](windows-source-review.md). Replacing Torch does not
automatically clear them.

## Next gates

1. Obtain and inspect the hosted Windows parity/native-module evidence. Investigate
   any difference or export failure before integrating the backend.
2. Complete exact runtime source/notice/native review and construct a Windows-only
   frozen service with the audited replacements. Preserve the reviewed macOS seed.
3. Build a new private NSIS setup, verify its exact installed OCR, tokenization,
   dictionaries, kanji, uncached translation, persistence, dependencies and model
   exclusion, then provide its SHA-256 and short PC checklist.
4. Repeat required Windows 11 installer/scaling tests on that exact setup and obtain
   maintainer approval through the protected human gate. Previous setup results
   cannot approve the new runtime. Only then integrate the joint main publisher.

No PC retest is needed for this prototype. Long Torch source audits remain
manual-only and are not invoked by it. The cancelled old source run and the
maintainer-requested deletion of all 58 historical runs are recorded in
[the cleanup record](windows-actions-history.md); historical Actions links no
longer resolve, while already downloaded local evidence and private drafts remain.
