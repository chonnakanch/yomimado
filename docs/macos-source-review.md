# macOS corresponding-source review

Audit on 2026-10-05 of `bd8ca73`'s private build inputs: **not cleared for
redistribution**. The original manifest lists 364 components (280 Rust, 79
Python, 5 JavaScript); it misses the detector source, PyInstaller bootloader,
Python interpreter and the shared libraries embedded in wheels. The revised
generator adds detector/bootloader records and `native-libraries.json`, with
original binary-input hashes and paths relative to their wheel/interpreter.
Signing changes binary hashes; these are provenance hashes, not final DMG hashes.

## OpenCV gap resolved by replacement

The previous public `opencv-python==4.11.0.86` wheel contained FFmpeg 7.1 libraries and
`libx264.164.dylib`, `libx265.212.dylib`, GnuTLS and many other shared libraries.
Its `LICENSE-3RD-PARTY.txt` describes FFmpeg as LGPL, but querying the actual
`avcodec_license()` returns **GPL version 3 or later**. Its
`avcodec_configuration()` includes `--enable-gpl --enable-version3`, x264 and
x265. The generator records both answers. A wheel-level Apache identifier
does not cover these libraries. Do not treat the previous strict inventory
pass as licence clearance.

Before distributing this runtime, obtain each library's actual version,
upstream source revision, patches, build recipes and applicable notices from
the wheel publisher/build provenance. The ABI number in a filename is not an
exact source revision. Deliver the GPL/LGPL corresponding source and build
information. Alternatively, replace the OpenCV build with a verified build
without these optional video dependencies, then repeat the whole native audit,
bundle build and smoke tests. Do not simply delete dylibs: OpenCV links them.
Do not relabel that FFmpeg build LGPL or use a current Homebrew formula as
proof of its historical build inputs.

The release now requires the custom `4.11.0.86+yomimado.1` build described in
[the OpenCV recipe](macos-opencv.md). Its source archive is SHA-256 pinned;
videoio/FFmpeg/GStreamer/AVFoundation are disabled. System-Cocoa highgui remains
for the detector's unused `imshow` import. The installed wheel
passes exact module/static-dependency, absent video API, binary/notice hash
and system-only dynamic-link checks. Static dependencies are zlib 1.3.1,
libjpeg-turbo 3.0.3, libpng 1.6.43 and protobuf 3.19.1, from the same source
archive. The generated notices preserve their texts plus OpenCV's module
author notices, SoftFloat and MSCR; the wrapper's MIT text is retained.
The original archive, two version/notice changes, build recipe and binary
record are assembled into an ignored local `opencv-source-delivery.tar.gz`.
The final DMG rejects these removed video libraries and requires matching
OpenCV build provenance. This replaces the uncertain wheel rather than trying
to clear its historical FFmpeg build.

## Native source/notice review completed — 2026-10-06

All **114 unique native inputs** in the current frozen inventory have technical
source and notice evidence in
[the hash-bound review record](../THIRD_PARTY_LICENSES/macos-native-review.json).
The complete release-source delivery still requires final archive review and
sign-off; this native review does not publish or approve the installer.

| Input                                     | Completed review                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CPython/OpenSSL/liblzma, OpenCV and NumPy | The previous 72 source-built input reviews remain valid; sources, embedded notices and frozen input hashes match.                                                                                                                                                                                                                                                                                                                 |
| Pillow 11.3.0                             | Rebuilt from exact source with static libjpeg-turbo 3.1.1 and FreeType 2.13.3, using system zlib. JPEG, PNG, resizing and font rendering remain available. Optional AVIF/WebP/TIFF/JPEG2000/CMS/raqm/XCB dependencies are disabled. Full MIT/IJG/BSD/Zlib/FTL and embedded notices retained, including the FreeType and Independent JPEG Group acknowledgements.                                                                  |
| torchvision 0.23.0                        | Built from wheel source commit `824e8c8726b65fd9d5abdc9702f81c2b0c4c0dc8`. Optional image/video codecs disabled; CPU/MPS operations and transforms remain. No bundled libc++ or codec dylibs. BSD, vendored giflib and OpenBSD reallocarray notices retained.                                                                                                                                                                     |
| PyTorch 2.8.0                             | Exact wheel source commit `a1cb3cc05d46d198467bebbb6e8fba50a325d4e7`; root plus 67 recursive CPU/MPS dependency repositories retained. Seven unused GPU/Android submodules and 2,264 unneeded model/media/font fixtures are explicitly omitted. Full wheel LICENSE/NOTICE covers static dependencies. OpenMP is replaced with source-built LLVM 15.0.7 and its full exception/legacy notices. Parallel Torch and NMS checks pass. |
| Shapely 2.0.7 / GEOS 3.11.4               | BSD binding and LGPL-2.1-or-later library notices retained. Upstream 2.0.7 recipe pins unmodified GEOS 3.11.4 (C API 1.17.4). Original sources and recipe retained; shared-library replacement tested successfully.                                                                                                                                                                                                               |
| Native Rust extensions                    | Exact sdists/local crates plus 743 distinct checksum-verified locked registry crates and commit-pinned missing notices retained. Includes Unicode, permissive licence choices and MPL covered source. Optional hf_xet profiling/pprof/inferno is disabled; CDDL source in its full lockfile is not linked into the app.                                                                                                           |
| Fugashi / MeCab, PyYAML / libyaml         | Matching source revisions, publisher build configuration, BSD/MIT copyright and full terms retained. MeCab library-only export omits unrelated dictionaries.                                                                                                                                                                                                                                                                      |
| Remaining C/Cython extensions             | Exact source distributions and native/static notices reviewed. Added SentencePiece's embedded Abseil/darts/esaxx/protobuf notices, libuv notices, Clipper/Boost terms, protobuf UTF-8 MIT terms and regex's Unicode 17 source data/notice.                                                                                                                                                                                        |
| wandb / compiled Tomli                    | Removed from frozen native inputs. The detector's tracked lazy training-import patch leaves inference independent of wandb; original detector checkout is untouched. Tomli uses its official pure-Python wheel.                                                                                                                                                                                                                   |

Native supplements live under `THIRD_PARTY_LICENSES/native/`. Their version and
SHA-256 index is checked when generating notices. A changed source archive,
binary input, notice, recipe or unexpected optional codec fails the existing
release verifiers. No new standalone script was added.

### Rebuild the minimal native dependencies

After preparing Python/NumPy, use the existing entrypoint:

```sh
rtk bash scripts/build-macos-prerelease.sh --prepare-native
```

It uses the reviewed original archives from the ignored source-delivery
collection: torchvision's exact source tree, Pillow 11.3.0, libjpeg-turbo 3.1.1,
FreeType 2.13.3, LLVM OpenMP/CMake 15.0.7 and the original pure-Python Tomli
wheel. The source archive includes those inputs, pinned CMake/Ninja versions,
compiler/SDK, compile options, complete notice aggregation, wheel and binary
hashes, and both existing build entrypoints. Developer ID credentials are not
needed. Keep detector weights outside all build/source archives.

Pillow's optional formats are unavailable in this release runtime; the app's
screen-capture and OCR JPEG/PNG path is unchanged. The OpenMP replacement
retains PyTorch's shared-library ABI; frozen real OCR and translation remain
required validation.

### GEOS source and replacement

The source delivery retains `geos-3.11.4.tar.bz2`, the exact Shapely publisher
recipe at `ec8f6cd42d2f36a75808f8f44f4b8f08405f181a`, and a replacement-test
record. The source archive includes the complete LGPL text. YomiMado adds no
EULA restriction on modification or reverse engineering for debugging it.

Build GEOS as shared libraries with CMake `Release`, Apple Silicon, macOS 14
and `BUILD_TESTING=OFF`. Replace both `libgeos.3.11.4.dylib` and
`libgeos_c.1.17.4.dylib` in a private copy of Shapely's `.dylibs` directory.
Keep the same filenames and make the C library load its companion through
`@loader_path/libgeos.3.11.4.dylib` using `install_name_tool`. Ad-hoc sign changed
libraries with `codesign --force --sign -`; publisher keys are unnecessary.
The tested replacement passes intersection, union and buffer operations.
For the frozen app, replace the matching runtime copies/aliases and rebuild or
ad-hoc sign the app seal, or rebuild YomiMado with the modified Shapely/GEOS
installation. Keep dynamic linking and the library source/notices available
alongside the installer. A rebuilt/modified app can require per-app Gatekeeper
approval; this does not confer Developer ID notarization.

## Source candidate preparation

`scripts/prepare-macos-sources.py` gathers data for review without installing
packages or executing source archives. First vendor the complete Cargo lockfile
from `apps/desktop/src-tauri` (network access may be needed for non-macOS crates):

```sh
rtk cargo vendor --locked /absolute/path/yomimado/services/ocr/build/source-delivery/cargo-vendor
```

Then run from the repository root:

```sh
rtk services/ocr/build/release-venv/bin/python scripts/prepare-macos-sources.py apps/desktop/src-tauri/resources/ocr/notices services/ocr/build/source-delivery --cargo-vendor services/ocr/build/source-delivery/cargo-vendor
```

The collector checks vendored files against checksum-verified original `.crate`
archives and Cargo.lock, includes all original crate archives, verifies npm
tarballs against lockfile SHA-512 integrity, and downloads exact PyPI sdists
against registry SHA-256 values. Cached archives with changed hashes are
rejected. The custom OpenCV source delivery is separately pinned. CPython,
OpenSSL and
liblzma candidates share the runtime source archive with original tarballs and
build records. Run downloads with `SSL_CERT_FILE` pointing to the release
environment's pinned certifi bundle if the shell has no CA bundle configured.
Preserve the
original Cargo cache until preparation completes; it supplies the `.crate`
archives used to verify the vendor tree. The collector also exports the exact
project commit when the checkout is clean, and the exact detector revision
with all source code preserved. Detector weights, notebooks and example
artwork/fonts are omitted; `detector-source-omissions.json` lists those omissions
and is checksum-linked from the candidate record. Dirty checkouts are rejected
for source export. Commit preparation changes and rerun to export the project.

The current inventory has **362 components** (280 Rust, 73 Python,
5 JavaScript and detector/CPython/OpenSSL/liblzma sources), **114 unique native
inputs** and 9 aliases. The worksheet covers **477 entries**, including the
project. The collector reuses completed technical evidence only when source,
notice and original binary hashes match. All 114 native inputs are covered;
PyTorch/torchvision and transitive native sources are supplied by the reviewed
archives, rather than an unavailable PyPI sdist. The report regenerated from clean commit `02c0b3b` covers all 477 entries
with 75 distinct archives and **zero unresolved entries**. A fully populated
private worksheet and `BUILD.md` are ready for the complete delivery review;
reviewer/date remain blank. Project and filtered detector exports are included.
Regenerate the project export whenever the selected release revision changes.

These are private source candidates, not public release assets. Raw upstream
archives can contain extra data/example artwork; inspect their terms and omit
unneeded uncleared assets while documenting modifications before assembling
the final delivery. Preserve notices, exact code, needed submodules and build
inputs. The collector reuses completed native technical reviews; it never creates
`source-delivery.json` or signs off the complete release-source delivery. The
release validator still rejects an incomplete or unreviewed delivery.

### Assemble the complete delivery for review

Use the existing collector's assembly option after populating the worksheet;
it does not download, install or execute dependency code:

```sh
rtk services/ocr/build/release-venv/bin/python scripts/prepare-macos-sources.py apps/desktop/src-tauri/resources/ocr/notices services/ocr/build/source-delivery --assemble-delivery services/ocr/build/source-delivery-prepared-final
```

The destination must be new. Assembly verifies every candidate hash and the
inventory, then copies only the worksheet's referenced archives and matching
notices. It recursively omits source-only images, media, test fonts and model
fixtures from dependency archives. Original YomiMado icons/synthetic fixtures,
ICO build resources, Python `.pth` configuration, preferred code, lockfiles,
licences and notice text are retained. Invalid archive-shaped test fixtures
remain ordinary data. Unsafe archive paths or links stop preparation.

`source-asset-omissions.json` records original and delivery archive hashes and
each removed asset's path/hash. Cargo vendor checksum maps drop only the
recorded omitted assets. The original, hash-bound build-input candidates stay
private and unchanged. A filtered archive is a source delivery, not an original
registry/cache archive: do not place modified `.crate` archives in Cargo's cache
or claim that their bytes match the original registry checksum. Use the supplied
vendor source directories for the desktop build; unpack retained native-binding
crate sources into a separate vendor tree when rebuilding those bindings.
Source-only fixture tests that use omitted files are unavailable; normal
macOS build and runtime source is retained. Native build instructions must
distinguish the original input hashes from these filtered delivery hashes.

Assembly writes `source-delivery.worksheet.json`, retains blank reviewer/date,
and never creates the release-authorizing `source-delivery.json`. Technical
preparation is complete only after inspecting the results; the named human
review required by `macos-release.py` remains the final source-clearance step.
Use the exact clean release revision in the project export and worksheet.
Existing-Mac installed-app checks remain separate from source approval.

The first delivery preparation contains all **477 entries across 75 archives**.
It records **2,332 asset omissions and 9 vendor checksum-map changes**; an
independent comparison verifies **156,012 retained files** with no code/notice
changes. The filtered desktop vendor tree passes locked offline Cargo metadata
resolution. The release tools pass 70 tests and the unchanged OCR service passes
47 tests. The complete worksheet, `BUILD.md`, notices, original/delivery hashes,
omission record and content-verification report are in the ignored local
`services/ocr/build/source-delivery-prepared-final/` directory. The source copy
is ready for the named human review; no approval is recorded automatically.

### Maintainer approval — 2026-10-06

The maintainer explicitly approved the prepared source/licence delivery using
Git account **chonnakanch**: “approve with my git account name”. The approved
local `source-delivery.json` covers clean project revision `042360e` and passes
the release validator's full coverage/hash/notice checks. The original unsigned
worksheet is retained separately. The approval record is a project audit trail;
it does not require a legal name or assert a legal certification.

The source-cleared hobby candidate embeds that exact manifest and revision.
Its mounted disk-image/bundle and frozen-service smoke checks pass; installed-app
testing and publication remain pending. Additional source-package checks pass
for the extracted project frontend (existing Node tools), Rust against the
filtered vendor tree (259 crates, locked/offline), and a wheel from the filtered
Manga OCR sdist. Its preferred OCR source matches the installed code.
The complete app/all-native-dependency rebuild using only the filtered package
has not been verified; this limitation was disclosed before the approval and
remains recorded in the local rebuild report. Do not infer that test passed.

### Packaging follow-up — 2026-10-06

The `042360e` installer failed quarantined first launch because its linker-only
signature lacked an app resource seal. Commit `5120506` requests a complete
local ad-hoc seal before DMG creation and verifies the outer app and all native
signatures. The replacement passes exact mounted bundle/source/signature and
frozen-service checks, browser/Finder installation and per-app Open Anyway.
The matching delivery contains all 477 entries and 75 archives; only the
project archive changed. Its manifest retains the original approval revision
and records the technically verified packaging correction without claiming
another human approval. The 74 dependency archives and native review are
unchanged. Source filename: `YomiMado_0.1.0_sources_5120506.tar.gz`; SHA-256:
`0ca10a4cc5084d4778aa636e07c504db56dcf9baec87af2d37b00859803a2744`.
Installed-app testing and publication remain separate gates.

## Delivery alongside the GitHub Release

Use GPLv3 section 6(d): offer the source with equivalent free access alongside
the DMG and retain availability while distributing it. A moving `develop`
link or the automatic YomiMado GitHub source archive alone is insufficient.
Publish the exact project commit, dependency sources, build scripts/lockfiles,
notices, source-delivery manifest and SHA-256 values. Include installation and
rebuild instructions that allow modification/replacement; users do not need
the publisher's signing key to build their own version. Never put credentials,
detector weights, commercial manga fixtures or sample fonts into a source pack.

Review these groups explicitly:

- YomiMado GPL-3.0-only and comic-text-detector commit
  `440b978563c71b758e31aaa315d100faba1efa2f`: source and build/installation
  scripts. Include the detector files used by inference and their notices;
  omit unneeded example artwork/fonts and document those omissions. Record any
  changes. The build now rejects a dirty detector checkout.
- MPL-2.0: Rust cssparser, cssparser-macros, dtoa-short, option-ext, selectors;
  Python certifi and the MPL-covered parts of tqdm. Deliver the exact covered
  source and preserve notices. `cargo vendor --locked --offline` can provide
  the locked Rust sources; review Python source distributions separately.
- NumPy uses system Accelerate; the former GCC/OpenBLAS/libquadmath libraries
  are absent. Preserve its exact source and embedded permissive notices. If
  reverting to a public wheel, review the GCC runtime exception and the separate
  libquadmath LGPL source/relink requirements again.
- PyInstaller 6.16.0: preserve `COPYING.txt`, including its bootloader exception.
  Python interpreter and wheels: preserve their notices; review nested native
  code, statically linked components and data, including MeCab/UniDic,
  GEOS, PyTorch, Pillow and torchvision. The native list identifies dynamic
  binaries; package notices/build provenance must cover static code too.
- Apache/MIT/BSD/Unicode and other permissive dependencies: preserve required
  notices/attributions and review dual-licence choices. Avoid treating SPDX
  labels alone as notice evidence.
- EDRDG data is a separate CC BY-SA 4.0 work, shipped unchanged with attribution
  and licence text. Record the XML/header refresh date in release notes. Manga
  OCR and translation model notices remain separate from software licences.

`macos-release.py source-template` creates a review worksheet bound to the
generated inventory and exact project revision. Store it in a local source
delivery directory outside git, as `source-delivery.json`. Each component
(including every native binary) requires an actual source archive, its hash,
licence evidence and bundled notice paths. Multiple entries can share one
archive, for example a reviewed Cargo vendor archive. Native notice additions
go under `native-notices/` in this directory; the release build copies them into
the app. `BUILD.md` explains exact build inputs, patches and installation.
Record the reviewer and date only after inspecting archive contents and legal
compatibility. The validator checks coverage, hashes and safe paths; it cannot
verify a legal opinion or infer the correct source from a binary.

References: [GPLv3 and corresponding source](https://www.gnu.org/licenses/gpl-3.0.html),
[MPL 2.0 sections 3.1–3.2](https://www.mozilla.org/en-US/MPL/2.0/),
[FFmpeg licensing and enabled GPL components](https://ffmpeg.org/legal.html),
[PyInstaller 6.16.0 signing behavior](https://pyinstaller.org/en/v6.16.0/feature-notes.html#macos-binary-code-signing).
