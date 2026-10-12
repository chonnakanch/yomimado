# Windows prebuilt runtime investigation

Historical package investigation, reviewed 2026-10-10 after the maintainer
chose to avoid long source builds. **No compatible drop-in Torch replacement
was established among the packages below.** This is a bounded snapshot, not a
claim that no such package exists anywhere.

The selected alternative is now implemented: the private Windows candidate
uses CPU ONNX inference, and complete hosted installed checks pass. See
[the current release plan](windows-release.md) for the exact setup hash and
remaining licence, alignment and human gates. Torch 2.8.0+cpu and torchvision
0.23.0+cpu remain only in the export/parity reference environment; they are
excluded from the installed runtime. These findings explain that choice and
do not constitute approval of the original combined Torch service.

The target remains Windows 11 x64, CPython 3.11.17 and existing OCR/learning
behavior. A package's top-level BSD/MIT label does not clear its bundled native
libraries. Model, Python/native ABI, operator and frozen-service compatibility
must also be verified.

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

## Selected build path and release gates

The retired Windows Torch source-audit workflow and its exclusive tools,
manifests and tests are removed. Their history is recoverable at Git revision
`ee1b7f5`. The historical **Windows private candidate** exported and compared models
using prebuilt reference packages, then froze and tested the separate Torch-free
ONNX runtime. The shared [Release workflow](../.github/workflows/release.yml) now
uses this recipe directly; it does not compile Torch. The reviewed candidate completed in
46 minutes 8 seconds; future run duration is not guaranteed.

The maintainer cancelled the earlier source run and separately authorized
deletion of all 58 historical Actions runs; their identities are
[recorded](windows-actions-history.md). No new source build is required by this
package investigation. The macOS seed and publisher are preserved.

The ONNX route passed horizontal/vertical OCR and translation comparison, then
complete installed verification. Native permissions, source/notices coverage,
model exclusion and exact-installer human approval remain separate gates in
[the source review](windows-source-review.md). The latest tested candidate has
a confirmed rightward overlay offset; its correction needs fresh verification.
Microsoft redistribution entitlement and component terms also remain open.
Joint publication on `main` stays gated; old installer results do not transfer
to a changed runtime or setup hash.

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
