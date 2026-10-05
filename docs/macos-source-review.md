# macOS corresponding-source review

Audit on 2026-10-05 of `bd8ca73`'s private build inputs: **not cleared for
redistribution**. The original manifest lists 364 components (280 Rust, 79
Python, 5 JavaScript); it misses the detector source, PyInstaller bootloader,
Python interpreter and the shared libraries embedded in wheels. The revised
generator adds detector/bootloader records and `native-libraries.json`, with
original binary-input hashes and paths relative to their wheel/interpreter.
Signing changes binary hashes; these are provenance hashes, not final DMG hashes.

## Concrete gap

The installed `opencv-python==4.11.0.86` contains FFmpeg 7.1 libraries and
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
Do not relabel this FFmpeg build LGPL or use a current Homebrew formula as
proof of its historical build inputs.

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
  notices. Do not assume a GPL runtime means all application code has that licence.
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
