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

## Remaining native/source review

This resolves the identified OpenCV/FFmpeg input gap only. The complete release
source delivery below remains unreviewed, including other frozen native
dependencies. Python is now source-built; the complete archive still needs
final delivery review. Do not mark the whole licence gate cleared
from an OpenCV-only source archive or successful runtime smoke.

The follow-up inspection of the 2026-10-05 inputs identifies these concrete
remaining items:

| Input                                            | Evidence and next action                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| CPython 3.11.17 / OpenSSL 3.5.9 / liblzma 5.8.4  | Replaces Xcode Python 3.9.6 and LibreSSL. Original sources are checksum-pinned, build steps are tracked, OpenSSL/liblzma are static, and embedded notices plus binary hashes are retained. The rebuilt DMG and seven selected standard-library test groups pass. Review the original tarballs/build record in the final delivery.                      |
| NumPy 1.26.4                                     | Its bundled notice explicitly labels libquadmath **LGPL-2.1-or-later**, separately from libgcc/libgfortran's GCC runtime exception. The full LGPL 2.1 text was missing from that notice and is now added by the generator with a pinned upstream checksum. Exact GCC/OpenBLAS source/build provenance and replacement/relink instructions remain open. |
| torchvision 0.23.0                               | Its wheel contains only its own BSD notice while bundling libc++, JPEG, PNG, WebP/sharpyuv and zlib libraries. Runtime queries report PNG 1.6.39, WebP 1.3.2 and zlib 1.2.13; these establish versions, not patches/build provenance. Obtain the matching native notices and build inputs.                                                             |
| PyTorch 2.8.0 / torchvision 0.23.0               | Neither exact PyPI release offers an sdist. A top-level GitHub archive alone omits submodule sources; resolve the wheel's source revision, complete submodule tree and packaging recipe.                                                                                                                                                               |
| wandb 0.26.1                                     | Its package notice is MIT, but its three native inputs include Go/Rust tools. Inspect their embedded dependencies/build records and notices. Its sdist alone does not establish the compiled tools' complete sources.                                                                                                                                  |
| Pillow, Shapely/GEOS and other native extensions | Existing wheel notices are preserved; verify exact native/static input versions, patches and build recipes against the recorded binary hashes.                                                                                                                                                                                                         |

### PyTorch/torchvision source evidence collected

The installed Python 3.11 wheels report PyTorch commit
`a1cb3cc05d46d198467bebbb6e8fba50a325d4e7` and torchvision commit
`824e8c8726b65fd9d5abdc9702f81c2b0c4c0dc8`. Private candidates under
`services/ocr/build/source-delivery/` contain those exact Git trees.
`pytorch-2.8.0-source-candidate.tar.gz` includes 68 repositories: the root
and initialized CPU/MPS dependency submodules, recursively. Seven top-level
Android/CUDA/Vulkan/ROCm submodules remain uninitialized and are explicitly
listed in its `YOMIMADO-SOURCE-CANDIDATE.json`; it is not presented as a full
upstream source tree. `torchvision-0.23.0-source-candidate.tar.gz` contains
the exact root tree and its packaging scripts.

These are additional private candidates outside the registry-sdist report.
Their adjacent `*-source-candidate.json` records include revisions and archive
hashes. Inspect source-pack examples/data before any redistribution. Historical
wheel build inputs remain unresolved: torchvision's pinned packaging script
installs several Conda codec packages without exact build pins; its macOS
workflow references a moving `pytorch/test-infra` branch. Matching libc++,
JPEG/PNG/WebP/zlib and PyTorch OpenMP source/build provenance still needs
verification or a controlled replacement build. A source commit or successful
smoke alone does not resolve those binary inputs.

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

The local collection covers **280 Rust components** (569 crates in the full
cross-platform lockfile), **5 JavaScript packages**, and **78 of 80 Python
packages**, including the custom OpenCV delivery. PyTorch/torchvision remain
unresolved. The inventory has 369 components: 280 Rust, 80 Python, 5 JavaScript,
and detector/CPython/OpenSSL/liblzma sources. The `source-candidates.json` report remains unreviewed,
with 152 native entries and complete delivery review still pending. The project
and filtered detector exports are additional candidates, not review sign-offs.
Regenerate it when the package/native inventories change.

These are private source candidates, not public release assets. Raw upstream
archives can contain extra data/example artwork; inspect their terms and omit
unneeded uncleared assets while documenting modifications before assembling
the final delivery. Preserve notices, exact code, needed submodules and build
inputs. The collector never creates `source-delivery.json`, a reviewer sign-off
or native licence clearance. The release validator still rejects an incomplete
or unreviewed delivery.

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
- NumPy's bundled GCC runtimes: preserve GPLv3 and GCC Runtime Library
  Exception text, verify the exception's applicability and the wheel's bundled
  notices. Review libquadmath's separate LGPL-2.1-or-later source/relink terms.
  Do not assume a GPL runtime means all application code has that licence.
- PyInstaller 6.16.0: preserve `COPYING.txt`, including its bootloader exception.
  Python interpreter and wheels: preserve their notices; review nested native
  code, statically linked components and data, including MeCab/UniDic, OpenBLAS,
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
