# Windows runtime/source review — private preparation

Status: open. This document does not inherit the macOS approval, approve a
Windows binary, or attest to a test that has not run. A private candidate may
be assembled to inspect actual inputs; public distribution is blocked until
all entries below have concrete evidence.

The Windows lock selects exact CPython 3.11.17 sources, Python wheels and CPU
Torch/torchvision binaries. CPython 3.11.9 from setup-python is a build bootstrap
only. `windows-inputs.json` records original download hashes, Python external
source/binary commits, package versions and available upstream sdists. Registry
licence metadata is a discovery aid, not a licence review. NSIS uses the locked
Tauri CLI; Node 22.23.2, Rust 1.98.1, MSVC 14.44.35207 and SDK 10.0.26100.0 are
selected in the candidate workflow. The hosted runner image still changes;
record its version plus actual compiler/SDK and fail if selected tools disappear.

The source build uses CPython's unmodified PCbuild recipe with checksum-pinned
source/binary externals and no Tkinter. Its upstream OpenSSL 3.0.15 and libffi
3.4.4 binaries are inventoried separately. Preserve their exact source trees,
upstream Windows build scripts and redistribution terms; merely possessing a
matching version number does not prove corresponding-source coverage.

For each candidate, inspect `notices/windows-inventory.json` and
`windows-native-configuration.json`. The latter records compiler/vendor build
information (Torch/BLAS/OpenMP, NumPy, OpenCV, Pillow codecs and GEOS) from the
exact hash-pinned Windows environment, not guessed versions from macOS.

Run `37584983920` supplied an actual frozen inventory of 140 AMD64 PE files
and 201 original interpreter/wheel inputs. The compiler/vendor configuration
confirms CPU-only Torch with Intel MKL 2025.2, oneDNN 3.7.1 and OpenMP;
NumPy uses OpenBLAS `0.3.23-293-gc2f4bdbb` with GCC 10.3.0; OpenCV retains
IPP 2021.12.0 and static codecs; GEOS is 3.11.4. Pillow records FreeType 2.13.3,
LittleCMS 2.17, WebP 1.5.0, AVIF 1.3.0, libjpeg-turbo 3.1.1, zlib-ng 2.2.4,
OpenJPEG 2.5.3 and TIFF 4.7.0. These are build reports, not source approval.

Successful installed run `37721943728` at `79065df7ba34a3aaa4ddb3a1ebb30e164405742a`
now inventories **94 AMD64 frozen service PE files** and 201 original native
inputs. The installed desktop is AMD64; the NSIS setup/uninstaller use x86
host stubs. The installed learning smoke records **128 loaded modules** with
their actual paths/hashes and passes the native dependency gate without
developer Python or CUDA on PATH. Removed OS DLLs and unused torchvision
codecs/FFmpeg are absent from delivery; real OCR still passes. This verifies
runtime loading and deliberate exclusions, while corresponding-source and
licence approval remain open. Exact setup SHA-256:
`01a28c0f4964b2df1733814670b3024d8aa18c525b544965a50189ec25ecab0a`.
The [private draft](https://github.com/chonnakanch/yomimado/releases/tag/untagged-e4524b4cbafe468fe44d)
contains hash-verified notices/inventories and source preparation. Later source
collections described below still need assembly into final delivery. Full
diagnostics from this run are retained locally in ignored
`services/ocr/build/windows-run-37721943728/`; the downloaded diagnostic ZIP
matches GitHub's SHA-256
`3338d19da7239420cf791b506232e3a7e08ededaa6d9180fc7f675947eea93aa`.

Ninety of the 94 frozen files match original interpreter/wheel bytes. The four
remaining files below require explicit provenance rather than an inferred wheel
owner. The frozen EXE is modified by PyInstaller as expected; that explains why
its hash differs, but does not replace retained bootloader/build evidence.

| Installed runtime file | SHA-256                                                            | Open binding                                                                   |
| ---------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `msvcp140.dll`         | `0fa7eb792d3fbcf2233e4ea47e9144b9b1309ba8ed5d4731a72fffa8f4f556d6` | Identify the exact runner/app-local VC runtime origin and redistribution terms |
| `vcruntime140.dll`     | `4d292623516f65c80482081e62d5dadb759dc16e851de5db24c3cbb57b87db83` | Identify the exact runner/app-local VC runtime origin and redistribution terms |
| `vcruntime140_1.dll`   | `a113f192195f245f17389e6ecbed8005990bcb2476ddad33f7c4c6c86327afe5` | Identify the exact runner/app-local VC runtime origin and redistribution terms |
| `yomimado-ocr.exe`     | `3b4e7c05b84e88b421be9edece042f33bab3795ea979fb09bb3a87083f4dbc61` | Bind the PyInstaller bootloader, appended application and exact freeze recipe  |

The earlier inventory exposed copied Windows DbgHelp/WinTrust/UCRT/API-set DLLs.
The recipe removes these OS components and records their original hashes,
validates the runner's AMD64 system libraries, and requires installed loading
verification. [Windows DbgHelp is not redistributable](https://learn.microsoft.com/en-us/windows/win32/debug/dbghelp-versions).
[Windows 11 supplies and always uses its serviced UCRT](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment).
VC redistributables remain app-local and need separate exact redistribution
terms/provenance; removing OS DLLs does not approve those binaries.

The [native rebuild worksheet](windows-native-rebuild.md) gives exact source
revisions, proposed Intel-free builds and GEOS replacement requirements. Those
Intel-free builds remain unrun; the worksheet conveys no approval.
Independent progress on 2026-10-09: GEOS source/replacement run `37877467511`
at `a10db77ec91d5e1e0f96f444b0a98376c641774a` passes source/tool/notice
hash checks, native Windows CPython/GEOS builds, upstream CTest and a frozen
Shapely baseline/replacement probe. The application EXE and PYDs remain unchanged;
the probe checks synthetic geometry and actual loaded replacement DLL hashes.
This resolves execution of the isolated replacement method, without changing
the current installer or approving final source coverage. Full installed OCR
replacement, archive inspection and final source-delivery assembly remain open;
the worksheet records the exact diagnostic artifact identity and limitations.

The original `mkl-2025.2.0-py2.py3-none-win_amd64.whl` is pinned solely to
preserve its full Intel October 2022 binary licence and bundled third-party
texts, which Torch's wheel notice omits. Its SHA-256 is
`b6ec153e4a073421dbb52ef99c7be97e66cde0272e4a1e3569b090b6f0130253`;
no MKL wheel code is installed by this collection. The terms restrict modification
and reverse engineering. OpenCV's retained IPP also carries Intel binary terms.
These restrictions require resolving GPL compatibility and exact static vendor
scope before public distribution, rather than treating source collection or
ordinary binary redistribution permission as clearance. A source-built Windows
Torch without MKL/Intel OpenMP and OpenCV without IPP are concrete alternatives
if compatible distribution rights cannot be established. No replacement build
or compatibility decision is claimed yet.

The 2026-10-07 wheel audit inspected original bytes whose SHA-256 pins are in
`services/ocr/windows-inputs.json`. Counts below describe build inputs; the
frozen/installed inventory determines which files are delivered.

| Windows input          | EXE/DLL/PYD inputs | Exact embedded notice findings / public gate                                                                                                                                                                                                                            |
| ---------------------- | -----------------: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SudachiPy 0.6.10       |                  1 | No wheel licence files; verified Apache/MIT upstream texts now supplemented. Rust/vendor source review remains open.                                                                                                                                                    |
| Fugashi 1.5.2          |                  2 | Fugashi/MeCab notices present; exact MeCab binary/source/Windows recipe bound below. Final source delivery and static compiler-runtime terms remain open.                                                                                                               |
| NumPy 1.26.4           |                 20 | BSD/OpenBLAS/LAPACK and GPL GCC runtime exception texts present; full libquadmath LGPL supplemented. OpenBLAS/GCC sources and replacement recipe remain open.                                                                                                           |
| OpenCV 4.11.0.86       |                  2 | Full third-party notice present. FFmpeg plugin removed; identify retained IPP/static codec inputs and exact source/build coverage.                                                                                                                                      |
| Pillow 11.3.0          |                  8 | Full vendor notice present including FreeType. Verify exact Windows codec versions, source coverage and FreeType attribution choice.                                                                                                                                    |
| PyInstaller 6.16.0     |                  4 | GPL bootloader exception text present. Preserve bootloader source/build recipe and modified frozen EXE provenance.                                                                                                                                                      |
| Shapely 2.0.7          |                  6 | Full GEOS LGPL and Windows runtime notice present. Exact GEOS source and replacement/rebuild recipe remain open.                                                                                                                                                        |
| Torch 2.8.0+cpu        |                 16 | LICENSE/NOTICE present. `libiomp5md.dll`/stubs and static CPU vendors need exact licence/source/build mapping; absence of a standalone MKL DLL is insufficient.                                                                                                         |
| torchvision 0.23.0+cpu |                  8 | Only torchvision LICENSE present despite JPEG/PNG/WebP/zlib DLLs. The private recipe excludes its unused `image.pyd` and codec DLLs; `_C.pyd` imports only Torch, VC and OS libraries. Installed OCR must verify that exclusion before this gap is considered resolved. |

Additional Windows source preparation (2026-10-08): Fugashi's original
`windows.yml` selects chezou's `mecab-0.996-msvc-5` release. Its original
`mecab-msvc-x64.zip` has SHA-256
`ca7eb528c8bc9c5802152424d9e3a0d0e3ea0e47847e70e44d0caf9381722062`.
The `libmecab.dll` member is byte-identical to the frozen Fugashi DLL:
`d8ddc0791437ce8c4a187ae7c69a2f683ce423683b7a5ecfda1c4cef436c1cab`.
The release tag resolves to source commit
`337b0529850c4276e6d404aca70e8d35f3f3ba1d`; its original
[source archive](https://codeload.github.com/chezou/mecab/tar.gz/337b0529850c4276e6d404aca70e8d35f3f3ba1d)
has SHA-256 `af339b19ed2d755d6acf419d87588374b5a8598def0c9a6d1dc26406f5aab4d7`.
The source offers the BSD option already preserved by Fugashi. The exact
`mecab/src/Makefile.x64.msvc` and `ci/win/build.bat` are retained in that
archive, using MSVC 2015, `/MACHINE:X64` and a static `/MT` runtime. Source
binding is now established; Windows rebuilding and compiler-runtime terms
remain unverified. The vendor ZIP's IPADic data and executables are audit
inputs only and are not installed. Original archives are retained privately in
`services/ocr/build/windows-audit/`, pending assembly of the final source delivery.

The original Windows Torch and torchvision wheels' `version.py` files identify
`a1cb3cc05d46d198467bebbb6e8fba50a325d4e7` and
`824e8c8726b65fd9d5abdc9702f81c2b0c4c0dc8`, respectively. They match the
retained preferred-source roots; Torch's reported oneDNN revision also matches
the retained submodule `8d263e693366ef8db40acc569cc7d8edf644556d`.
This source identity comparison does not clear the different Windows static
vendors, Intel binary terms or build configurations.

The exact OpenBLAS commit named by NumPy's Windows DLL resolves to
`c2f4bdbbb43a1d20a7342f40122e18e573ce436a`. Its retained original
[source archive](https://codeload.github.com/OpenMathLib/OpenBLAS/tar.gz/c2f4bdbbb43a1d20a7342f40122e18e573ce436a)
has SHA-256 `9c0f2b8d1f6839f8b0d1309417e06d38eabfa76ba52d9fe80f79df496d5afddc`.
The retained original [GCC 10.3.0 preferred source](https://ftp.gnu.org/gnu/gcc/gcc-10.3.0/gcc-10.3.0.tar.xz)
has SHA-256 `64f404c1a650f27fc33da242e1f2df54952e3963a49e06e73f6940f3223ac344`.
NumPy's original build helper selects the Scientific Python nightly Windows
OpenBLAS vendor ZIP; that original vendor download currently returns HTTP 403.
The exact compiler patches, static libquadmath scope and replacement/relinking
recipe remain open. Collecting these source roots does not resolve them.

Pillow's pinned source archive contains its Windows dependency recipe
`winbuild/build_prepare.py`, SHA-256
`d8afecdf8faa2e63f85392439adb2c50a7235e51463af1d3659d54af0a36ff0c`.
The recipe matches the reported Windows codec versions and supplies its
compiler/linkage flags and patches. Fifteen original preferred-source archives
are now retained in `services/ocr/build/windows-audit/pillow-sources/`;
[the source-input record](windows-native-source-inputs.json) binds their URLs,
SHA-256 values and embedded licence-file hashes. This includes FreeType's
PNG/Brotli/HarfBuzz inputs, TIFF's XZ input and libavif's AOM 3.12.1,
dav1d 1.5.1, libyuv `4db2af62dab48895226be6b52737247e898ebe36` and
libsharpyuv/libwebp 1.5.0 inputs from the original CMake recipes. The original
WebP download's certificate hostname mismatch was not bypassed; preferred
sources were obtained from the recipe's official Chromium repository instead.
Exact static binary binding, licence review, final source delivery and a
source-only Windows rebuild remain open. No macOS codec clearance is reused.

The SudachiPy 0.6.10 tag resolves to
`7e2f287bbfffc036421cf960802e41a696727747`. Its original
[preferred-source archive](https://codeload.github.com/WorksApplications/sudachi.rs/tar.gz/7e2f287bbfffc036421cf960802e41a696727747)
is retained with SHA-256
`40694b5d3d7541a08629484af8383b0afc134977b3680de002d14bfa71a3a095`.
Its Cargo.lock (`8fe375cb8712bb8f219f1ce7b4dd4faa560d3d247b2ff8b8f88c1b4e685179f8`)
is stale relative to the Python binding manifest: the manifest requires PyO3
0.23, while the lock records 0.22.6. The original PyPI sdist omits Cargo.lock.
Do not treat the retained lock/vendor collection as the exact Windows wheel's
dependency graph. Resolve the actual wheel build inputs from upstream evidence,
or build the binding on Windows with a deliberately resolved, reviewed and
retained lock and crate originals. Source identity alone does not close this gap.
The actual Windows PYD has SHA-256
`9654018fcc2d5fb244d6195b59435042fc6fd8a924c3d0d790acee1cb2dc1a68`.
Its embedded Rust source paths identify PyO3/PyO3-FFI **0.23.3**, 22 other
crate versions and compiler commit `90b35a6239c3d8bdabc530a6a0816f7ff89a0aaf`.
Twenty-seven original crate archives (including three additional PyO3 family
members for preparation) are retained under `windows-audit/sudachi-crates/`,
verified against crates.io checksums; the source-input record includes their
licence-file hashes. Embedded paths are partial evidence, not proof of the
complete dependency graph or a successful Windows rebuild.

Review steps:

1. Every actual EXE/DLL/PYD needs a SHA-256, x64 machine value, imports and
   matching input provenance. The PyInstaller bootloader and modified frozen
   executable need explicit build evidence when hashes differ from the wheel.
2. Review exact wheel licences and all embedded native notices: NumPy's BLAS
   and compiler runtime, OpenCV codecs/IPP, Torch CPU/OpenMP/BLAS, torchvision,
   Pillow codecs/fonts, GEOS, Fugashi/MeCab, tokenizer binaries and CPython's
   OpenSSL/libffi/SQLite/bzip2/zlib/liblzma/Expat/libmpdec. Identify actual linked
   components before deciding whether different binaries/source builds are needed.
3. The unused torchvision image/codec extension and optional OpenCV FFmpeg plugin are removed from the frozen bundle because
   still-image DNN inference does not need it. Retain original wheel hashes and
   this recipe; confirm the installed inventory contains no FFmpeg plugin and
   that OCR still works. Removal does not approve other OpenCV native inputs. `windows-excluded-native.json` retains the removed inputs' paths/hashes.
4. Preserve full licence/NOTICE texts and preferred sources, exact recipes,
   patches, build tools and archive hashes. Review submodules/vendor libraries;
   a PyPI sdist may not include native wheel vendors or complete build inputs.
   Include applicable LGPL replacement/relinking instructions. Identify MSVC
   runtime redistribution permission separately; it has no open-source archive.
5. The exact WebView2 SDK 1.0.3650.58 is pinned from Microsoft NuGet. Its
   BSD redistribution licence and NOTICE are preserved, with the loader DLL
   and static library hashes (the MSVC wrapper statically links the latter).
   The missing webview2-rs MIT text is fetched at Cargo's exact upstream commit.
   All three locked wrapper crates are linked to that preserved notice; the
   macros crate's different upstream revision was verified to have identical
   licence bytes. The Windows-target locked graph resolves 286 crates.
   Resolve SDK-loader source/system-library scope separately; wrapper metadata
   does not cover Microsoft binaries.

   `windows-desktop-sources.json` records Windows Cargo membership, copied
   licence texts and original archives checked against Cargo.lock. Installed
   npm inputs (including build tools) retain notices and original tarballs
   verified against package-lock SHA-512. The macOS crate subset is not Windows
   coverage. `windows-installer-inputs.json` separately records the installed
   desktop, setup and actual NSIS cache inputs, including its x86 host/plugins.
   Resolve exact NSIS plugin/stub and WebView2 loader source/terms before public
   delivery; metadata and collected archives alone do not grant approval.
   The selected NSIS 3.11 original source and `nsis_tauri_utils` 0.5.3 source
   commit `13d9edd27b69310e108d6fbd49f90992f8a05390` are checksum pinned. Their
   full COPYING/MIT/Apache texts are copied into installed notices before NSIS
   packaging. Bind the compiled stub/plugin and recursive build inputs before
   approving source coverage; this collection does not attest to a rebuild.
   Missing SudachiPy software texts and NumPy's full LGPL supplement are copied
   from checksum-verified upstream notices. This resolves missing texts only.

6. Bind every notice/source entry to installed binary hashes and the exact
   project revision. Do not sign off unresolved entries, placeholders or broad
   upstream links. The private source-preparation archive is an evidence
   collection, **not a completed corresponding-source delivery**.

Model/data assets have their own pinned Windows manifest. Detector weights
are forbidden in staged resources and delivery artifacts. The detector code
is pinned to `440b978563c71b758e31aaa315d100faba1efa2f`, copies source without
artwork/weights and applies the published inference-only lazy wandb patch.
Manga OCR's example image is replaced with an original blank warmup image.
The two Apache model revisions retain model credits and licences. EDRDG data
retains CC BY-SA/EDRDG attribution; review the exact Windows snapshot dates.
Changing dictionary bytes does not silently update a pin. If the upstream daily
snapshot moves, supply the pinned original locally or prepare a deliberate new
snapshot with updated hashes and a new candidate.

`publicDistributionApproved` and `installedAppVerified` remain false in private
provenance. No public Windows release path exists yet. After technical/source
review and maintainer installer results, extend the protected single publisher
for both platforms. Full source-only rebuilding remains unclaimed until run.
