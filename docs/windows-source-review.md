# Windows runtime/source review — private preparation

Status: open. This document does not inherit the macOS approval, approve a
Windows binary, or attest to a test that has not run. A private candidate may
be assembled to inspect actual inputs; public distribution is blocked until
all entries below have concrete evidence.

Source artwork exclusion — 2026-10-11: Manga OCR 0.1.16's original reference
sdist contains 27 example/test manga JPEGs. The ONNX path excludes Manga OCR
from the frozen runtime. Its source delivery now retains all unchanged code,
recipes and the original Apache-2.0 licence in a canonical archive with preferred
source SHA-256 `24879e3a7fca28d3181378309f66cfe2008e988b66b02b5a7300955cedcdede6`.
Every excluded image has a recorded original path/hash; the raw sdist is omitted
from the final source bundle so those images cannot reappear through that copy.
No licence for the original manga artwork is inferred from the software licence.
For reference-only source rebuilding, `scripts/create-manga-ocr-warmup.py`
provides a synthetic replacement warmup image. Final archive inspection remains
required before public distribution.

Installer plugin preparation — 2026-10-11: the original NSIS Tauri 0.5.3 source
archive omits its dependency lock. The [short Windows recipe](windows-nsis-runtime.md)
now builds that unchanged source with a deliberately resolved seven-crate graph,
15 original notices and offline Cargo verification. The official CLI 2.11.5
template is pinned; only plugin lookup changes. Exact rendered-template and
embedded-DLL checks must pass on Windows. NSIS 3.11's own COPYING is separately
verified: zlib/libpng, bzip2 and CPL-1.0 LZMA with its linking exception; the
selected installer compression is zlib. No long Torch build is introduced.

Additional exact-input checks — 2026-10-11: NumPy 2.4.6's own preferred source
and 25 original notices are now retained; the export-only 1.26.4 source does not
cover this runtime. PyYAML 6.0.3's [exact Windows release recipe](https://github.com/yaml/pyyaml/blob/49790e73684bebad1df05ef8d828fa12f685bffb/.github/workflows/ci.yaml)
selects static LibYAML 0.2.5. Its preferred source, original MIT licence and
Windows CMake recipe are retained with exact hashes; native configuration must
report that same version. Protobuf 6.33.6's embedded `utf8_range.c` is bound by
hash to its full Google MIT-style copyright/permission/disclaimer supplement.
The official pure-Python Tomli 2.4.1 wheel replaces its four unneeded compiled
modules; all four Python files match the original sdist. Local source/notice
checks and 210 release-tool tests pass. Final installed binary and archive
verification remain open; no macOS approval is inherited.

Native preparation — 2026-10-11: exact evidence from run `38072170793` now
establishes final-Python horizontal/vertical OCR, three fresh translations,
NumPy 2.4.6 CPU ONNX execution without Torch, source-built Sudachi and canonical
VC replacement binding. The service inventory contains 84 AMD64 files. The app
compiles, but NSIS fails near its 2 GB limit, so installed verification remains
open. The recipe excludes the two hash-verified export-only weight files after
parity and retains all four inference graphs. Native direct-class and Wry ABI
probes pass for the [MIT WebView loader](windows-webview-loader.md); its full
installed integration is under test. These are Windows findings, independent
of macOS approval.

Additional Python Rust source delivery now binds the original Cargo.lock files
in the four exact `pydantic_core`, `safetensors`, `tokenizers` and `watchfiles`
sdists to **284 original registry crates** and **540 notice files**. All original
crate hashes and full notice copies verify locally, including optional and
non-Windows lock entries. Two originals omit their full licence files;
[checksum-pinned supplements](windows-python-rust-notice-inputs.json) come from
the exact upstream commits named in each original `.cargo_vcs_info.json`:
[wasi-rs](https://github.com/bytecodealliance/wasi-rs/tree/3da562c06214feafc14d37bf290671636caa6718)
and [wit-bindgen](https://github.com/bytecodealliance/wit-bindgen/tree/f2393e6e98fa5f9236cac580db8a3fc9de6a4b70).
Original archives, lock identities, supplements and preparation recipes are
retained for offline source delivery. No long native build is introduced.
This closes an omitted dependency-source preparation gap; final archive bytes,
installed notices and full source-only rebuild remain separate checks.

Microsoft runtime follow-up — 2026-10-11: [the component review](windows-microsoft-runtime.md)
separates conditional VC redistribution rights from GPLv3's System Library
definition and conflicting FSF explanatory guidance. A short read-only Windows
provenance job compares the six observed VC DLL hashes with canonical REDIST
inputs. It changes no installed runtime or licence and approves no candidate.
Exact new files, distributor entitlement/end-user terms and the separate
WebView2 loader assessment remain open.

Sudachi preparation — 2026-10-11: [the small locked binding recipe](windows-sudachi-runtime.md)
replaces the incomplete old wheel graph with deliberately resolved, retained
inputs. All 62 original crates and 128 notice files verify locally, and the
Windows dependency graph resolves offline. Windows compilation and installed
tokenization must pass before this closes the old wheel-source gap. This is
independent of the rejected long Torch build.

The new Windows-only [NumPy 2.4.6 input](windows-numpy-runtime.md) binds the
actual BLAS DLL to its original tagged supplier wheel and preferred sources.
That supplier's original Windows patch and linker-map gate explicitly exclude
static libquadmath. Original software/vendor notices and full GCC exception
texts are retained. This replaces the old NumPy 1.26.4 source/relinking concern
described below; final installed DLL identity and numerical/OCR parity remain
required. No macOS input or human approval changes.

Current runtime preparation — 2026-10-10: the maintainer rejects long Torch
source builds. **Windows ONNX feasibility** passes at `4d49cb7` in run
`38047950684` (4 minutes 6 seconds). The new private candidate removes Torch/
torchvision from inference, uses prebuilt CPU ONNX Runtime 1.22.1, and selects
the independently audited IPP-free OpenCV source recipe. New installed inventory,
native loading and fresh exact-installer approval remain required. Older Torch
inventory and compatibility findings below describe historical candidates.

The [ONNX native input manifest](windows-onnx-native-inputs.json) now binds the
official v1.22.1 source revision, Windows CPU packaging recipes, exact vcpkg
baseline/overlay ports, older FlatBuffers override and 25 vendor/build-helper
source archives. All 25 archives match original port SHA-512 recipes as well as
retained SHA-256 pins. The manifest includes full original notice-file hashes.
The source collector preserves code/recipes, original notices and explicit
test-model/media/prebuilt-binary exclusions; canonical tree hashes are checked
independently before delivery. MLAS uses in-tree CPU kernels; DNNL defaults off;
the global recipe defines `EIGEN_MPL2_ONLY`. The original generic wheel notice
is retained unchanged, including entries for components not selected by this
CPU recipe. Exact final wheel/loaded-DLL identity and compiled vendor scope
still require the candidate evidence. These source/recipe findings are not an
assertion of complete binary-build attestation or public approval.

First frozen ONNX attempt `38048563546` at `51a7b23` reaches resource validation
after final-Python parity, then rejects an ONNX Runtime bundled example model.
The freezer is narrowed to runtime modules/binaries and metadata; arbitrary
ONNX files remain prohibited. No installer or public release resulted.

The downloaded successful prototype artifact `11668511516` matches GitHub
SHA-256 `3beab1d4ae20e3ba89f0333bd85688a8f73176e897621b13924bcfbd9df2d796`.
Its actual ORT build string identifies commit `89746dc19a`, matching the retained
v1.22.1 preferred source. Runtime imports exclude Torch and its three fresh
translations and complete synthetic OCR responses match the baseline. This is
bootstrap Python 3.11.9 evidence; final installed coverage remains separate.

The frozen-service inventory now reads the pinned literal `EXE-00.toc` without
executing it, checks the selected AMD64 bootloader against the exact original
PyInstaller wheel member, compares its executable code section with the frozen
EXE, and requires the EXE to end with the exact recorded application PKG bytes.
Original Analysis/EXE/PKG/PYZ records and the generated spec are retained with
hashes in delivery notices. This permits expected resource/checksum edits while
rejecting changed bootloader code or application bytes. Preferred bootloader
source/build recipes are supplied by the already pinned PyInstaller sdist;
hosted execution of this new check remains required.

Downloaded OpenCV preparation evidence from `38049828336` matches GitHub SHA-256
`25b870fd2781df8f21ea85b7a64c46c03e090c55293c5e8d59dbeae80d8ae937`.
Its isolated native/frozen CPU probes pass with IPP disabled. The original
producer emitted nested notice keys with Windows backslashes, incompatible with
the strict portable retention manifest. Those keys and source references now
use forward slashes; escaping notice paths remain rejected.

Run `38062747049` confirms that same retention failure after the frozen build;
downloaded artifact `11674014358` matches GitHub SHA-256
`b99bcc636962e1077d2e99c79709776c0558cfc04a517eb2d60ee35c2de7acdb`.
Its final Python 3.11.17 comparison passes complete OCR and three fresh translation
parity with no Torch imports, plus cache survival after a new service instance.
The producer correction above addresses its actual exception. The next candidate
also retains [48 pinned native source archives](windows-native-delivery-inputs.json):
Pillow's 15 codec/vendor inputs, 27 observed Sudachi crate originals, OpenBLAS,
GCC 10.3.0, MeCab, Sudachi, the historical OpenBLAS build recipe and GEOS 3.11.4.
Local collection verifies every original archive, canonical preferred-source
hash and notice hash, producing 340,089,987 bytes of compressed source delivery
and 168 original notice files. Models, artwork and prebuilt binaries are omitted
with explicit hash records. The installed notice copy and source archive receive
the same preparation record, manifest and collector recipes.

Compressed inputs are read in a single streaming pass before canonical sorting;
all 27 existing ONNX native preferred-source hashes remain unchanged. This avoids
repeated decompression of large compiler archives. Collection executes no vendor
source or compiler. These source records close missing delivery inputs, while
the exact Sudachi dependency graph, compiler-runtime scope, Microsoft runtime
redistribution and installed binary bindings still require the review below.
Source and public approval remain false.

The subsequent source-download check in run `38064440449` rejects the historical
raw Gitiles WebP archive hash. The new delivery manifest now uses the existing
`gitiles-tar-v1` recipe and exact source commits for WebP, AOM and libyuv. Fresh
downloads of all three pass the canonical input, preferred-tree and original
notice checks; preferred-source hashes remain unchanged. Variable transport
metadata is not accepted as a change to source bytes.

Four added pure Python runtime packages now have original preferred sources:
FlatBuffers 25.2.10, coloredlogs 15.0.1, humanfriendly 10.0 and pyreadline3 3.5.4.
Their 75 wheel Python files match the source bytes exactly. FlatBuffers' PyPI
sdist omits its licence, so the retained official source commit
`1c514626e83c20fffa8557e75641848e1e15cd5e` supplies the unchanged full Apache
text and matching Python files. Source preparation now has 52 archives and
explicit wheel/source code hashes; empty original-notice selections are rejected.
The [native replacement instructions](windows-native-replacement.md) are copied
into installed notices and included in project sources. Their historical GEOS
test scope and still-open OpenBLAS/compiler gap remain explicit.

The [original-runtime GPL review](windows-gpl-compatibility.md) now records the
actual detector-to-OpenCV/Torch calls, loaded binary hashes, exact Intel terms
and exception checks. Public distribution of this combination conflicts with
the FSF's published GPL interpretation; no applicable detector linking permission
was found. This is a release review decision, not a judicial finding about past
private testing. Compatible replacement libraries or sufficient rights-holder
permission can resolve it; a source rebuild is the selected route, not the only one.

Latest automated inspection — 2026-10-10: [run `38022182370`](https://github.com/chonnakanch/yomimado/actions/runs/38022182370)
at `65ac794370fe2b0f60d7ed968ac0be2c04ca4d51` passes the complete hosted suite
and private upload checks. Downloaded artifact `11660046107` (124,199 bytes)
matches GitHub SHA-256
`b573952fce9a392da72f7a41b2fb3e106c5d58820909af614b4fd9b9891b6aa8`.
Available raw checksums and setup/provenance identity verify; setup SHA-256:
`4639a6351eb8ec708cc824fe96c98a0e1f82ccf304eb1e9641d19823a6d1782d`.
There are 94 AMD64 service PE files and 347 input records (201 original
interpreter/wheel entries plus 146 freezer-discovered entries). Exactly 93 frozen
files now have hash-identical original input bindings; the modified service EXE
still needs explicit bootloader/build coverage. All 82 app-local loaded-module
hashes match. The current pinned input manifest, complete installed UI and frozen
learning/persistence checks pass. Desktop SHA-256:
`f3f9a745308e868f2a642d7a199642829edaa6cb1771555355abab0358a0f11d`;
service SHA-256: `c885adf456a54f87cd1b3f33c34545c55c0d35fab8310be09f7cb2e4e9709c18`.
Actual DLL origins are now established below, without approving redistribution
terms. No new native replacement is bundled by this candidate, and no manual
results apply to its rebuilt setup. Actual setup/source/notices archive bytes
remain undownloaded locally. Reports stay private under
`services/ocr/build/windows-run-38022182370/`.

Earlier automated candidate inspection — 2026-10-10: [run `38019354851`](https://github.com/chonnakanch/yomimado/actions/runs/38019354851)
at `87731d65c50499a67ec7683e889402638ba557ca` passes every build, installed UI,
OCR/learning/persistence and private-draft upload/hash step. Downloaded evidence
artifact `11658311143` (111,186 bytes) matches GitHub SHA-256
`38f3c13e714d2f704118b4705484d9749da37a9b59de5e7254a24d88517d3593`.
The available raw checksum entries verify. Provenance and installer-input records
agree on setup SHA-256
`5db98f6b460d71367ff88f4f17c976ac62239b97fde56d92fe8f67c9dee31443`.
All 94 service PE records are AMD64, and all 82 actually loaded installed-runtime
hashes match the inventory; 46 other/system modules are recorded separately.
The current pinned input manifest matches. Installed startup/quit cleanup,
horizontal/vertical geometry, tokenization, dictionaries, kanji, uncached
translation and saved/cache restart pass without developer Python or CUDA on PATH.
The AMD64 GUI desktop hash is
`b2be8dd1de4752d90e08eb72fb0b096401a735935ba91b51ea35640abc1a3b21`;
the frozen service hash is
`69c6b414b08a1bfdb6c23bf1566e41ba876c6da3ae97892d7c506d9635d4d84f`.
The notice supplement is prepared and staged in this private candidate. The
actual setup/source/notice archives have not been downloaded for local inspection.
This remains a private preparation build with source/native and human approval
false; maintainer results below apply only to the older `51b0091103c1…` setup.
Reports are retained privately in `services/ocr/build/windows-run-38019354851/`.

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

Current exact-candidate inspection (2026-10-09): run `37802965979` at
`c69eff996f7e85ea88ecb4f0407e05cf5d8ec8b5` retains the same **94 AMD64
service PE files**, 201 original native inputs and 128 actual loaded modules.
The downloaded `windows-preparation-evidence` ZIP (ID `11563655639`, 109,829
bytes) matches GitHub SHA-256
`7da2a72053ce9522904b07f2100b9c7e7594545e173d8d5504cc48d3eac5119c`.
Its checksum/provenance and installer inventory bind the maintainer-tested setup
`51b0091103c10c03ecd3748039bd4db0631381fb43885fe7163b889821fba207`.
All actually loaded app-local service hashes match the frozen inventory.
Installed geometry covers both orientations; tokenization, dictionaries, kanji,
uncached translation, saved-data/cache restart, bundled startup and quit cleanup
pass without Python/CUDA on PATH. The desktop is AMD64, GUI subsystem, unsigned;
setup/uninstaller retain x86 host stubs. Original CPython build outputs differ
from the earlier run and must use this candidate's exact inventory. Reports are
retained privately in `services/ocr/build/windows-run-37802965979/`.

Ninety of the maintainer-tested setup's 94 frozen files match original interpreter/wheel bytes. The four
remaining files below require explicit provenance rather than an inferred wheel
owner. The frozen EXE is modified by PyInstaller as expected; that explains why
its hash differs, but does not replace retained bootloader/build evidence.

| Installed runtime file | SHA-256                                                            | Open binding                                                                                 |
| ---------------------- | ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| `msvcp140.dll`         | `0fa7eb792d3fbcf2233e4ea47e9144b9b1309ba8ed5d4731a72fffa8f4f556d6` | Hash-identical MSVC 14.44.35207 input identified below; redistribution terms remain open     |
| `vcruntime140.dll`     | `4d292623516f65c80482081e62d5dadb759dc16e851de5db24c3cbb57b87db83` | Hash-identical hosted Python 3.11.9 input identified below; redistribution terms remain open |
| `vcruntime140_1.dll`   | `a113f192195f245f17389e6ecbed8005990bcb2476ddad33f7c4c6c86327afe5` | Hash-identical hosted Python 3.11.9 input identified below; redistribution terms remain open |
| `yomimado-ocr.exe`     | `c9911d9abe692c86f9de803af9f97cbb59af10339583dd86c8a673f036b73398` | Bind the PyInstaller bootloader, appended application and exact freeze recipe                |

The earlier inventory exposed copied Windows DbgHelp/WinTrust/UCRT/API-set DLLs.
The recipe removes these OS components and records their original hashes,
validates the runner's AMD64 system libraries, and requires installed loading
verification. [Windows DbgHelp is not redistributable](https://learn.microsoft.com/en-us/windows/win32/debug/dbghelp-versions).
[Windows 11 supplies and always uses its serviced UCRT](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment).
VC redistributables remain app-local and need separate exact redistribution
terms/provenance; removing OS DLLs does not approve those binaries.

Additional provenance preparation — 2026-10-10: the Windows inventory now reads
PyInstaller 6.16.0's literal `Analysis-00.toc` using that exact version's schema.
It records each actual native source path, destination, SHA-256 and PE imports,
including DLLs discovered outside interpreter/wheel inventories. Exact hash
matches join the existing frozen `buildInputs`; the original TOC and freeze
recipe digests remain in `freezeAnalysis`. Parsing executes no TOC code and
rejects malformed records, unsafe/duplicate Windows destinations and absent
sources. Tests retain the exact source hash/path and reject those invalid cases.
This is prepared for a new hosted candidate; the previously recorded VC origins
remain open until Windows evidence is downloaded and reviewed. Source paths do
not grant redistribution rights, and the modified service EXE's bootloader/build
binding remains a separate gate. macOS inventory/packaging is unchanged.

Hosted provenance verification now passes in run `38022182370`. Its 146 freezer
inputs identify `msvcp140.dll` under the pinned MSVC **14.44.35207**
`VC/Tools/MSVC/.../bin/HostX64/x64` directory and both `vcruntime140` DLLs under
the runner's hosted **Python 3.11.9 x64** bootstrap directory. Their source and
installed hashes exactly match the three values in the table above. The inventory
retains full absolute input paths, destinations and PE imports. This closes the
missing origin evidence, while exact Microsoft redistribution terms and final
source/runtime approval remain open. The source-built CPython 3.11.17 interpreter
is still the actual service; its copied VC DLLs differ from those selected by
PyInstaller. The freeze recipe digest matches the current source. The TOC digest
is retained, but its original bytes are not part of the downloaded textual evidence.

The [native rebuild worksheet](windows-native-rebuild.md) gives exact source
revisions, independent Intel-free builds and GEOS replacement requirements.
The new **Windows Torch source audit** pins original CPU source gitlinks, the
previously missing Eigen 3.4.0 archive, full notice hashes and build tools, then
checks native CPU tensors and actual PE/loading evidence. Its hosted execution,
matched torchvision and full frozen/installed recognition remain unverified;
the worksheet conveys no approval. The separate
**Windows OpenCV source audit** now prepares a pinned static PYD without IPP,
then checks synthetic geometry, actual CPU detector inference and a frozen
probe's loaded-native paths/hashes. Original source/vendor notice pins are in
`docs/windows-opencv-build-inputs.json`. Run `37934320710` passes native/frozen
geometry and detector inference without IPP; its downloaded evidence hashes,
notices, actual modules and source/recipe bindings are verified locally. Inspection
also exposes OpenCV's still-enabled static CRT default despite the requested DLL
linkage. That is explicitly disabled, with generated compile-command and actual
PE import checks added for the next run. Corrected run `37938195277` passes:
its downloaded evidence ZIP hash, recipe/cache/notice hashes, all 648 DLL-runtime
compiler commands, actual AMD64 VC imports and native/frozen detector outputs
are independently verified. Full installed OCR/source delivery remains
unverified; the tested installer is unchanged.
Independent progress on 2026-10-09: GEOS source/replacement run `37877467511`
at `a10db77ec91d5e1e0f96f444b0a98376c641774a` passes source/tool/notice
hash checks, native Windows CPython/GEOS builds, upstream CTest and a frozen
Shapely baseline/replacement probe. The application EXE and PYDs remain unchanged;
the probe checks synthetic geometry and actual loaded replacement DLL hashes.
This resolves execution of the isolated replacement method, without changing
the current installer or approving final source coverage. Full installed OCR
replacement and final source-delivery assembly remain open. The hash-verified
diagnostic ZIP is now inspected locally: all 431 upstream tests pass, retained
cache/recipe/probe hashes match and actual replacement DLL hashes match the PE
inventory. Original sources and full notices still need final delivery assembly;
the worksheet records the exact diagnostic artifact identity and limitations.

Subsequent exact installed replacement passes in run `38021809403`, with its
downloaded evidence independently verified: all original/replacement loaded GEOS
paths/hashes, both OCR orientations, learning/persistence, 5,400 other unchanged
installed files and exact restoration. See the native worksheet for replacement
hashes and scope. Final source/notices assembly, replacement packaging and human
approval remain open; the downloadable setup is unchanged.

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
if compatible distribution rights cannot be established. The original combination's
compatibility decision and its limits are recorded in the linked review above;
no completed Torch replacement or final Windows source approval is claimed.

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

Notice follow-up on 2026-10-10: inspection of the exact Pillow Windows wheel's
aggregate `LICENSE` finds twelve vendor sections, but no AOM licence/patent text.
The AVIF recipe enables local AOM, dav1d, libyuv and libsharpyuv. The Windows input
manifest now pins four already collected source archives (AOM, dav1d, libyuv and
libwebp/libsharpyuv) and seventeen full original licence/patent texts. The notice
collector verifies archive and member hashes, requires regular files and preserves
their paths and bytes under `licenses/windows-python-vendors/`. Those original
archives also enter the private source-preparation archive. All seventeen copies
are verified locally; changed text, archive links and escaping paths are tested.
The existing wheel notice remains intact. Additional AOM source-tree notices are
retained without claiming every source-tree component is compiled into Pillow.
This closes the concrete supplemental-text preparation gap; the tested installer
does not yet contain the supplement. Exact static linkage, complete source review
and verification of a newly packaged installer remain open. A Pillow rebuild is
not required solely to add these notices.

Installed-file binding is separately verified against the current exact setup's
retained inventory: all **seven** bundled Pillow PYDs (including `_avif`) are
byte-identical to their corresponding members of the pinned Windows 11.3.0
wheel. Its eighth native member, `_imagingmorph`, is absent from the frozen
runtime. The eight-input wheel count above is not the installed-file count.
This establishes which wheel supplies those PYDs; it does not independently
prove the complete statically linked vendor source graph.

Private candidate run `38016054660` stops before compilation because the generated
Gitiles libwebp archive has changed tar timestamps. A fresh response contains the
same 341 file contents as the retained original; its compressed/archive hashes
differ. The three Gitiles source inputs now select exact upstream commits and use
an explicit `gitiles-tar-v1` canonical tar format: sorted paths, unchanged contents,
file types and permission bits, zero timestamps/owner fields, and no variable PAX
metadata. The complete canonical archive must match its pinned SHA-256 before it
is accepted. Links, duplicate/escaping paths and unexpected modes are rejected.
Fresh libwebp, AOM and libyuv downloads all match the independently computed pins
and original notice hashes. Original collected archive digests remain recorded.
Dav1d keeps its original byte-level archive check. Registry wheels, models and
dictionaries keep the existing exact-byte check. A test proves timestamp changes
are accepted while changed source bytes are rejected. Hosted rerun `38016673211`
at `902bcf6d3446fbeab65128cfa62ac93f5549a051` now passes preparation, freezing,
NSIS building, installed startup/resource verification and frozen OCR learning/
persistence. Its installed UI and private-draft staging steps fail; source/public
gates remain open. GitHub retains evidence artifact `11657230994` (111,299 bytes),
declared SHA-256
`74534086117b2628efafc2b676156638f48912640c8a5997990017b2f147f674`.
Downloaded on 2026-10-10: the artifact's bytes match that SHA-256. Provenance
and installer-input records agree on exported setup SHA-256
`0129393b970cc4b5c55628b9fc308b3733e25daabe1b0d4cc8e61cfd861f2fe2`.
All 94 service PE records are AMD64; all 82 loaded installed-runtime modules
match their inventory hashes, with 46 other/system modules recorded separately.
The manifest hash matches the unchanged pinned input manifest. Seven Pillow
PYDs remain present. Installed synthetic horizontal/vertical OCR, tokenization,
dictionaries, kanji, uncached translation and saved/cache restart checks pass.
The UI report completes three capture cases, then stops at **page-scan button**;
its exception is missing. Failure diagnostics are now retained for future runs.
Actual setup bytes, source/notices archives and successful private upload are
not independently verified by this textual artifact. The newer `87731d65c504`
run passes all five UI cases and staging without changing application behavior
or test expectations; the older failure causes remain unestablished.
Current manual results remain bound only to the
unchanged setup hash recorded above. Reports are retained privately under
`services/ocr/build/windows-run-38016673211/`.

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
