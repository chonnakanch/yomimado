# Windows prebuilt runtime investigation

Follow-up: the maintainer selected an isolated ONNX experiment. Its initial
[local comparison](windows-onnx-prototype.md) passes the bounded OCR/translation
fixtures without Torch in the inference process. Windows execution, final
native/source review and installed packaging remain open; this does not change
the drop-in Torch findings below.

Reviewed 2026-10-10 following the maintainer's decision to avoid long source
builds. **No compatible drop-in Torch replacement has been established in the
packages checked below.** This is a bounded investigation, not a claim that no
such package exists anywhere. No alternative binary has been installed, executed,
added to the candidate or approved for public distribution.

The target remains Windows 11 x64, CPython 3.11.17, CPU inference and existing
OCR/learning behavior. The current environment pins Torch 2.8.0+cpu and
torchvision 0.23.0+cpu. A version change must also establish Python/native ABI,
operator, model, Transformers and frozen-service compatibility. A package's
top-level BSD/MIT label does not clear its bundled native libraries.

## Package findings

| Publisher / package                                        | Evidence and decision                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Official Torch 2.8.0+cpu Windows CPython 3.11 wheel        | The already inspected wheel SHA-256 is `7631ef49fbd38d382909525b83696dc12a55d68492ade4ace3883c62b9fc140f`. Installed evidence reports MKL 2025.2; its `torch_cpu.dll` is hash-identical to the wheel. The [existing compatibility review](windows-gpl-compatibility.md) still applies. CPU-only does not mean MKL-free.                                                                                                                                                                                                                                                                                                                                                                                                    |
| Conda-forge Torch/libtorch 2.8.0, Windows x64              | The publisher's [Torch metadata](https://api.anaconda.org/release/conda-forge/pytorch/2.8.0) lists 12 Windows CPU builds, including three CPython 3.11 builds; its [libtorch metadata](https://api.anaconda.org/release/conda-forge/libtorch/2.8.0) lists three Windows CPU builds. All use `cpu_mkl`. Dependencies explicitly include `libblas * *mkl`, `mkl` and `intel-openmp`. These packages do not remove the MKL concern. The broader [publisher index](https://api.anaconda.org/package/conda-forge/pytorch) contains 517 Windows x64 files in the retrieved snapshot; every filename includes `mkl`, with no `generic` variant. This is an index check, not execution or full licence clearance of every version. |
| Older official Conda Torch 2.5.1, Windows CPython 3.11 CPU | [Exact metadata](https://api.anaconda.org/release/pytorch/pytorch/2.5.1) for `pytorch-2.5.1-py3.11_cpu_0.tar.bz2`, SHA-256 `3b7cd50e1de205b4992ec502c19f03cc67f2d1b93476d4f0e91ecda133acf672`, requires `blas * mkl`, `mkl 2023.1.*` and `intel-openmp`. Downgrading to it does not establish a compatible replacement.                                                                                                                                                                                                                                                                                                                                                                                                    |
| Newer official Windows CPU build recipe, Torch 2.14.0      | The [dependency recipe](https://github.com/pytorch/pytorch/blob/v2.14.0/.ci/pytorch/windows/build_install_deps.py) installs `mkl-include`/`mkl-static`; the [environment recipe](https://github.com/pytorch/pytorch/blob/v2.14.0/.ci/pytorch/windows/build_env_setup.py) deliberately makes MKL discoverable for CPU builds. This is recipe evidence, not a downloaded 2.14 wheel audit. Upgrading alone provides no demonstrated MKL-free route.                                                                                                                                                                                                                                                                          |
| Microsoft `torch-directml` 0.2.5.dev240914                 | Its [publisher metadata](https://pypi.org/pypi/torch-directml/0.2.5.dev240914/json) requires `torch==2.4.1` and `torchvision==0.19.1`. It is an extension that still needs Torch. Microsoft's [instructions](https://learn.microsoft.com/en-us/windows/ai/directml/pytorch-windows) target DirectX GPU execution. This does not establish a solution for the CPU-only milestone or pinned runtime.                                                                                                                                                                                                                                                                                                                         |
| Bytedeco JavaCPP native PyTorch packages                   | A potentially useful native-library lead, but not a drop-in Python runtime. The [pinned current recipe](https://github.com/bytedeco/javacpp-presets/blob/95c3c9504cb56fe51eb67b75262811bd99b41c3e/pytorch/cppbuild.sh) selects OpenBLAS but changes `build_python=True` to `build_python=False`. The inspected 1.5.12 recipe for Torch 2.7.1 also disables Python bindings. The [Maven release index](https://repo.maven.apache.org/maven2/org/bytedeco/pytorch/maven-metadata.xml) has no Torch 2.8.0 release. This lead requires matching Python/torchvision bindings and full native/source review; borrowing its DLLs for current wheels is not approved.                                                              |
| Community `theIvanR/torch-on-clunkers` wheels              | The publisher's [README](https://github.com/theIvanR/torch-on-clunkers/tree/ee6c1bd0b17bed4b188c6dac6ec6df59101fa7f5) advertises CUDA builds. Its [pinned recipe](https://github.com/theIvanR/torch-on-clunkers/blob/ee6c1bd0b17bed4b188c6dac6ec6df59101fa7f5/pt_build.cmd) enables CUDA and MKLDNN. No matching CPU-only binary with complete native permissions/source provenance was established. No externally hosted wheel was downloaded or executed.                                                                                                                                                                                                                                                                |

Installing `nomkl`, replacing NumPy's BLAS, setting a runtime flag or deleting
an MKL-named DLL cannot establish removal of statically linked MKL from existing
Torch. The same caution applies to IPP in the original OpenCV wheel.
Apache-licensed oneDNN and separately licensed MKL must be reviewed individually;
a name containing `MKLDNN` alone does not prove proprietary MKL.

## Build policy

**Windows Torch source audit** now has no push trigger. It retains a manual
dispatch with `allow_long_source_build` defaulting to false; compilation requires
an explicit true value on `develop`. The maintainer has chosen not to use that
route during this investigation. Updating the workflow does not cancel an
already running job from an older commit.

**Windows private candidate** is a separate installer workflow. It already
installs pinned prebuilt Torch wheels and does not call the Torch source builder.
Its previous roughly 30-minute duration does not imply a time guarantee for a
new runtime. The macOS seed path and publisher are unchanged.

The maintainer cancelled source run `38040678348`; the public API confirmed
`cancelled`. On subsequent explicit instruction, all 58 historical Actions runs
were deleted and their identities were [recorded](windows-actions-history.md).
No subsequent long source run was dispatched by this investigation.

## Remaining decision and release gates

For a drop-in prebuilt route, the concrete blocker is obtaining an exact
Windows x64 Python Torch binary with compatible native permissions, matching
bindings, notices and corresponding-source/build coverage. The checked packages
do not satisfy it. The original installer remains private.

Two further avenues avoid a full Torch source build:

1. Investigate a different prebuilt inference runtime, such as ONNX Runtime, for
   **both recognition and local translation**, and remove Torch/torchvision use
   from the detector path. This is a backend migration, not a package substitution.
   First prove the existing local models, generation/tokenization and horizontal/
   vertical OCR geometry in an isolated prototype; then review exact runtime/model
   inputs and repeat the complete installed tests. No feasibility pass is claimed.
2. Obtain sufficient additional permission for the exact original combined
   runtime from the relevant GPL rights holders. No contact was made and no grant
   is claimed; this is an external permission route, not an automated approval.

Neither avenue bypasses the other native source/notices gaps in the
[source worksheet](windows-source-review.md), exact-installer human gate or
requirement to exclude detector weights. A new runtime requires a new private
installer/hash and fresh tests; results bound to `51b0091103c1…` do not
automatically transfer. Joint publication on `main` remains gated.

## Evidence retained

Original API responses and pinned recipe bytes are retained in the ignored local
directory `services/ocr/build/windows-prebuilt-review-20261010/` with retrieval
URLs and SHA-256 in `retrievals.json`. Representative response/source hashes:

| Evidence                              | SHA-256                                                            |
| ------------------------------------- | ------------------------------------------------------------------ |
| Conda-forge Torch 2.8.0 metadata      | `df6c945ee0baf873c339600799a57fcd89f9ea5c88b1574d908cf336456cb487` |
| Conda-forge libtorch 2.8.0 metadata   | `f365927d3317f268cfb8bb6ced8a41d2d0816a5a28c6c0450988081430c5b115` |
| Conda-forge full Torch package index  | `794a636813eb22e1134056bf4cfb76a6adabd86c37e4cb2a20f1d047af16af5e` |
| Bytedeco current pinned native recipe | `527ea39cb13d82f7c63dc7725f24446ecb2243a4b9c0ae80a4b693e4dfc98902` |

Metadata can change. These hashes identify inspected snapshots;
published metadata alone is not native binary or legal approval.
