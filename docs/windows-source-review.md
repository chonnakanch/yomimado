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

The 2026-10-07 wheel audit inspected original bytes whose SHA-256 pins are in
`services/ocr/windows-inputs.json`. Counts below describe build inputs; the
frozen/installed inventory determines which files are delivered.

| Windows input          | EXE/DLL/PYD inputs | Exact embedded notice findings / public gate                                                                                                                                                                                                                            |
| ---------------------- | -----------------: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SudachiPy 0.6.10       |                  1 | No wheel licence files; verified Apache/MIT upstream texts now supplemented. Rust/vendor source review remains open.                                                                                                                                                    |
| Fugashi 1.5.2          |                  2 | Fugashi and MeCab notices present. Preserve exact MeCab source and Windows recipe for its hashed DLL.                                                                                                                                                                   |
| NumPy 1.26.4           |                 20 | BSD/OpenBLAS/LAPACK and GPL GCC runtime exception texts present; full libquadmath LGPL supplemented. OpenBLAS/GCC sources and replacement recipe remain open.                                                                                                           |
| OpenCV 4.11.0.86       |                  2 | Full third-party notice present. FFmpeg plugin removed; identify retained IPP/static codec inputs and exact source/build coverage.                                                                                                                                      |
| Pillow 11.3.0          |                  8 | Full vendor notice present including FreeType. Verify exact Windows codec versions, source coverage and FreeType attribution choice.                                                                                                                                    |
| PyInstaller 6.16.0     |                  4 | GPL bootloader exception text present. Preserve bootloader source/build recipe and modified frozen EXE provenance.                                                                                                                                                      |
| Shapely 2.0.7          |                  6 | Full GEOS LGPL and Windows runtime notice present. Exact GEOS source and replacement/rebuild recipe remain open.                                                                                                                                                        |
| Torch 2.8.0+cpu        |                 16 | LICENSE/NOTICE present. `libiomp5md.dll`/stubs and static CPU vendors need exact licence/source/build mapping; absence of a standalone MKL DLL is insufficient.                                                                                                         |
| torchvision 0.23.0+cpu |                  8 | Only torchvision LICENSE present despite JPEG/PNG/WebP/zlib DLLs. The private recipe excludes its unused `image.pyd` and codec DLLs; `_C.pyd` imports only Torch, VC and OS libraries. Installed OCR must verify that exclusion before this gap is considered resolved. |

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
