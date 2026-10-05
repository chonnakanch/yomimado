# Source-pinned macOS NumPy

The first Apple Silicon release uses NumPy **1.26.4**, compiled from its
original source distribution against macOS's **Accelerate BLAS/LAPACK**.
The public wheel bundled OpenBLAS, libgcc, libgfortran and LGPL-2.1-or-later
libquadmath with unresolved historical source/build provenance. Those four
libraries are absent from this replacement; do not copy or delete them from
a stock wheel to imitate the build.

NumPy 1.26 supports the updated Accelerate interface on macOS 13.3 and later;
YomiMado's minimum is macOS 14. See
[NumPy's release notes](https://numpy.org/doc/1.26/release/1.26.0-notes.html).
The public version remains 1.26.4. A separate build record distinguishes the
replacement by actual binary hashes, options and notices; matching the version
string alone does not pass release verification.

## Build and retained evidence

Use the existing entrypoint after preparing the source-built Python runtime:

```sh
rtk bash scripts/build-macos-prerelease.sh --prepare-numpy
```

`--prepare-runtime` also performs this step for a newly prepared environment.
No extra standalone build script is required. Sources and records are ignored
under `services/ocr/build/numpy-source/`; build tools live in a separate
`build/numpy-build-venv/`, outside the frozen runtime and notice inventory.

The original `numpy-1.26.4.tar.gz` has SHA-256
`2a02aba9ed12e4ac4eb3ea9421c420301a0c6460d9830d74a9df87efa4912010`.
The builder validates this before extracting/compiling. It uses Apple Clang,
the selected Xcode SDK, deployment target 14.0, and these Meson options:

```text
-Dblas=accelerate
-Dlapack=accelerate
-Duse-ilp64=true
-Dallow-noblas=false
```

Pinned build tools: Cython 3.0.8, meson-python 0.15.0, Meson 1.3.2,
Ninja 1.11.1.1, packaging 26.3 and pyproject-metadata 0.7.1.
They are build inputs, not newly bundled runtime packages. The compiler/SDK,
options, wheel hash and every installed extension's original hash are recorded.
The original source is unchanged. Wheel packaging aggregates NumPy's BSD notice,
source licence files and embedded pocketfft/dragon4 copyrights, including the
random generators' notices, then updates the wheel's RECORD hashes.

The ignored `numpy-source-delivery.tar.gz` contains the original sdist, exact
build entrypoint, build record and aggregated notice. Current SHA-256:
`ad1d14405aab335a1449aa2b512581c1de70619de435e2b88736e7d6235d6dcc`.
The original sdist also retains build-tool and source-only notices. Final
project source delivery includes the matching committed entrypoint and locks.

Release-environment checks reject changed sources, recipe, options, compiled
inputs, notice text, bundled dylibs or non-system dynamic links. Mounted-bundle
checks require the NumPy build record, match all frozen input provenance and
the embedded notice, and reject any NumPy dylib. No LGPL supplement is copied
for this build because it contains no libquadmath; the original full text stays
in the repository for historical/public-wheel review.

## Verification — 2026-10-05

- 19 installed NumPy extensions link only macOS system libraries; the frozen
  service includes 13 of those inputs and zero NumPy dylibs.
- NumPy's linear algebra, FFT and random suites: **1,820 passed, 12 skipped,
  1 expected failure**.
  Test tools stay outside the release environment. Cython extension tests need
  both build tools and release NumPy visible to the subprocess Python.
- Release-tool rejection tests, OCR-service tests, the native app/DMG build and
  the exact mounted frozen-service smoke pass. The smoke checks real OCR
  geometry, dictionaries, tokenization, translation and restart persistence.

This completes the NumPy input review, not the entire release-delivery review.
See the [release checklist](macos-release.md) for remaining native inputs and
installed-app checks. Detector weights are still user-installed.
