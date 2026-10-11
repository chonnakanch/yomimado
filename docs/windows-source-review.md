# Windows runtime/source review — private preparation

Status: open. This document does not inherit the macOS approval, approve a
Windows binary, or attest to a test that has not run. A private candidate may
be assembled to inspect actual inputs; public distribution is blocked until
all entries below have concrete evidence.

Final downloaded delivery inspection — 2026-10-11: successful Windows run
`38133593809` attempt 2 at `8c46366d04e96d5356c250605e7ea936db209eb3` verifies the exact
installed CPU ONNX runtime, native inputs, NSIS plugin, WebView loader and
canonical VC copies. The frozen service's 80 PE files are AMD64; its bootloader,
service code and application package have separate binding records. CPU ONNX
execution, geometry, learning and restart persistence pass without developer
Python/CUDA or a bundled detector model.

The downloaded `windows-source-preparation.tar.gz` has SHA-256
`8a3d170f77e2c4f242890dab35e62e19c47c13d58e3ce6d6a94cf314b59cfea8`;
`windows-notices.tar.gz` has
`003876ac910258ad006ab5281604ff5d854c16d255b33beaf686d719fcd314bb`.
Inspection of their actual bytes verifies all **56 native preferred-source
archives**, **284 Python Rust registry archives and 540 notices**, and the
original NSIS plugin archive plus its **seven registry inputs and 15 notices**
(with the plugin's two own licence texts retained separately). The archive
contains **27 ONNX preferred-source inputs, three port files and 48 original
notices**, all verified against their pinned hashes. These checks are recorded
with the downloaded delivery evidence. The source-built Sudachi archive and all
62 registry inputs/full notices also verify. The new archives contain 1,035
regular source-delivery members and 1,880 regular notice members; each is hashed
locally without extracting or executing upstream code. The preferred Manga OCR
archive retains its pinned delivery hash; the raw image-containing sdist is absent.
No detector-model filename occurs in the outer source archive, and packaged
resource/model-exclusion checks pass.
This is actual delivered-source/notices verification, not inherited macOS approval.

Independent full source-only rebuilding is **unverified**; no byte-identical
rebuild or blanket legal approval is claimed. The maintainer accepts the linked
Community 2022 terms but has not yet obtained a copy; [Microsoft-only distribution conditions](windows-microsoft-runtime.md)
remain unresolved. The maintainer confirms the corrected setup's SHA-256,
alignment at 100%, 125% and 150% and all listed local installer checks pass in
[the installed test record](windows-installed-test.md). That closes the local
test checklist without granting Microsoft redistribution entitlement or
approving the protected publisher.
Keep the candidate private. Source/public
approval flags remain false pending final distribution review and protected
human approval. This summary replaces the per-attempt preparation timeline;
the earlier records remain recoverable in Git.

## Actual installed inputs and retained coverage

The current service is CPython 3.11.17 with CPU ONNX Runtime 1.22.1 and
NumPy 2.4.6. Torch/torchvision are export/reference inputs only and are absent
from the installed process. Exact compiler, runner, PE imports, loaded paths,
original input hashes and freeze records accompany each private candidate.
Windows licences are assessed independently of the macOS seed.

| Component                       | Actual-input/source and notice evidence                                                                                                                                                             | Limit or next gate                                                                                                                          |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| CPython and externals           | Original 3.11.17 PCbuild sources and hash-pinned externals; original Windows OpenSSL 3.0.15/libffi 3.4.4 binaries and their sources/recipes retained                                                | Matching versions alone do not establish a binary/source binding; use each candidate's actual inventory                                     |
| PyInstaller service EXE         | Literal Analysis/EXE/PKG/PYZ records; exact original AMD64 bootloader member/code section and appended application PKG verified; original preferred sources/recipe retained                         | Modified EXE bytes are bound separately from unchanged wheel/interpreter inputs                                                             |
| CPU ONNX Runtime                | Build revision `89746dc19a` matches the v1.22.1 source; 27 preferred-source archives, exact vcpkg/FlatBuffers ports and 48 original notices verify                                                  | Retained upstream build graph is not independent byte-identical build attestation                                                           |
| NumPy/BLAS                      | [NumPy 2.4.6 review](windows-numpy-runtime.md), exact tagged OpenBLAS supplier, compiler exceptions, patches/recipes and 25 NumPy notices retained; installed CPU/numerical/OCR checks pass         | Do not apply the rejected older NumPy 1.26.4 static-libquadmath findings to this replacement                                                |
| OpenCV                          | [Pinned minimal build](windows-opencv-build-inputs.json), actual generated DLL-runtime compiler flags, IPP/video/GPU exclusions, native/frozen probes and source/vendor notices verify              | Preserve the active build/probe scripts; generic wheel licence metadata does not describe the selected native build                         |
| Sudachi binding                 | [Locked short build](windows-sudachi-runtime.md), 62 original crates and 128 notices; original software source and deliberate dependency lock retained; installed tokenization passes               | Old prebuilt wheel's stale/incomplete graph is not used as approval                                                                         |
| Other Python Rust extensions    | Four original sdist Cargo locks bind 284 original crates and 540 notice files; checksum-pinned wasip2/wit-bindgen supplements cover omitted full texts                                              | Original archives and non-Windows/optional lock entries remain available; full source-only rebuild unverified                               |
| Pillow/codecs                   | Exact Windows 11.3.0 wheel members bind installed PYDs; `winbuild/build_prepare.py`, 15 vendor inputs and missing AOM/dav1d/libyuv/libwebp notices retained                                         | Full upstream notices remain unchanged; do not infer codec licensing from the Pillow software licence                                       |
| GEOS/Shapely and Fugashi/MeCab  | Exact original native bindings, preferred sources/build recipes, original notices and [replacement instructions](windows-native-replacement.md) retained                                            | Shared-library replacement scope is distinct from Microsoft's compiler-runtime entitlement                                                  |
| PyYAML/LibYAML                  | Exact PyYAML 6.0.3 Windows release recipe selects LibYAML 0.2.5; preferred source, MIT text and CMake recipe retained; final native configuration matches                                           | Actual linked vendor version controls review                                                                                                |
| Protobuf and pure Python inputs | Protobuf 6.33.6 embedded utf8_range source binds to full Google permission/disclaimer supplement; Tomli 2.4.1 pure wheel matches sdist; four extra Python packages' 75 files match original sources | Metadata is discovery evidence, not blanket vendor approval                                                                                 |
| Desktop Cargo/npm               | Windows-only Cargo graph, original registry archives/notices and npm tarballs verified against Cargo.lock/package-lock; installed desktop binding retained                                          | The macOS dependency subset is not Windows coverage                                                                                         |
| WebView loader                  | [Source-only loader](windows-webview-loader.md), MIT implementation, retained SDK headers/BSD notices, direct/Wry ABI probes and all copied Cargo static-library hashes verify                      | The SDK loader object is replaced; wrapper licence metadata alone did not cover it                                                          |
| NSIS host/plugin                | [Installer record](windows-nsis-runtime.md), original NSIS 3.11 source/COPYING and zlib compression; source-built plugin's exact embedded DLL, lock, seven original crates and 15 notices verify    | i686 setup host/plugin is intentional; desktop/service are AMD64; no independent byte-identical rebuild claimed                             |
| Microsoft VC runtime            | Ten unchanged canonical VC143 originals and standard/renamed copies verify against [the exact manifest](windows-vc-runtime-inputs.json)                                                             | Linked Community terms accepted; licensed copy not obtained yet; [distribution terms](windows-microsoft-runtime.md) remain a public blocker |

The ONNX input manifest preserves exact CPU packaging recipes, vcpkg baseline
and override ports. MLAS uses in-tree CPU kernels, DNNL defaults off, and the
upstream recipe defines `EIGEN_MPL2_ONLY`. The original generic ORT wheel notice
is retained unchanged, including entries not selected by that CPU recipe.
Canonical preferred-source hashes and exclusions preserve code/build inputs
while removing test media, model fixtures and prebuilt binaries. These records
are not a claim of an independently reproduced upstream wheel.

The [native source manifest](windows-native-source-inputs.json) and
[canonical delivery manifest](windows-native-delivery-inputs.json) preserve
original inputs and exact licence-file hashes. The collector handles Gitiles
transport timestamp variations only through a pinned canonical recipe and
unchanged file-content checks; changed preferred-source bytes are rejected.
Corresponding-source review includes vendor/submodule code, original build
recipes, patches, compiler exceptions and applicable relinking instructions.
The downloaded archive checks above establish actual delivered bytes.

Fugashi's retained MeCab `mecab-0.996-msvc-5` release input has original ZIP
SHA-256 `ca7eb528c8bc9c5802152424d9e3a0d0e3ea0e47847e70e44d0caf9381722062`;
its `libmecab.dll` matches the original native binding
`d8ddc0791437ce8c4a187ae7c69a2f683ce423683b7a5ecfda1c4cef436c1cab`.
Preferred source commit `337b0529850c4276e6d404aca70e8d35f3f3ba1d` has archive
SHA-256 `af339b19ed2d755d6acf419d87588374b5a8598def0c9a6d1dc26406f5aab4d7`.
The BSD option and original `mecab/src/Makefile.x64.msvc`/`ci/win/build.bat`
are retained; this recipe uses MSVC 2015 and static compiler-runtime linkage.
Its vendor ZIP's IPADic data and executables are audit inputs, not installed
assets. Compiler-runtime distribution conditions remain separate.

## Assets and exclusions

Detector weights are forbidden in installed resources and delivery. Only
hash-checked temporary smoke input is used on the Windows runner and removed
at completion. Detector code remains pinned to
`440b978563c71b758e31aaa315d100faba1efa2f`, without artwork/weights and with
the published inference-only lazy wandb patch. Its GPL software obligations
remain separate from the user's model file.

Manga OCR's raw 0.1.16 reference sdist contains 27 manga images. Final delivery
instead contains its unchanged preferred code/recipes and Apache-2.0 text,
preferred-source SHA-256
`24879e3a7fca28d3181378309f66cfe2008e988b66b02b5a7300955cedcdede6`.
The 64-member delivered archive contains no image assets; the raw sdist is
absent. Each excluded image has an original path/hash record. Synthetic warmup
creation is provided for reference-only rebuilding; no artwork licence is
inferred from the software licence.

The two Apache model revisions retain original model credits/licences. The
runtime retains four bound inference graphs after export/reference parity;
the two original PyTorch weight files are excluded only after that check.
EDRDG dictionaries and Sudachi/UniDic resources have their separate notices
and pinned snapshot identities. Daily upstream changes are rejected, not
silently repinned. Model/data terms are not inferred from package metadata.

OS DbgHelp, WinTrust, UCRT/API copies, unused video/codec extensions, Torch,
MKL/IPP and arbitrary ONNX example models are excluded from this runtime.
`windows-excluded-native.json`, resource hash records and installed native
loading checks retain the actual exclusion/input evidence. Removing one
component does not approve another component's terms.

## Remaining public gates and retained history

1. Resolve the maintainer's Microsoft redistribution grant and component-only
   end-user/distributor requirements. The [notice draft](windows-microsoft-distribution-notice.draft.md)
   is not an accepted agreement or active installer licence page.
2. Verify the Windows-only overlay shadow correction in the new hosted/private
   setup and obtain the exact-hash visual/scoped PC results. Retain the verified
   prior functional pass and the explicitly untested hardware cases.
3. Complete final distribution review and protected exact-installer human
   approval before enabling the single publisher for both platforms.

`publicDistributionApproved` and `installedAppVerified` remain false in private
provenance. No Windows public publisher is enabled. Full source-only rebuilding
and byte-identical reproduction remain unclaimed.

The retired Torch source-build experiment and historical per-attempt reports
remain recoverable from Git revision `ee1b7f5`; they are not the current runtime
or a task still waiting to be completed. The [original GPL review](windows-gpl-compatibility.md)
and [prebuilt investigation](windows-prebuilt-runtime.md) preserve why the
old combined runtime was replaced. Required source/notices and active build,
verification, export/parity and replacement recipes remain in the branch.
