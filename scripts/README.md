# Script roles

## Current release and checks

[Checks](../.github/workflows/checks.yml) runs the shared release and macOS CI
tests. [Release](../.github/workflows/release.yml) builds both platforms and keeps
one owner-approved publisher. Its script entrypoints are:

- `desktop_release.py`: pinned input transfer, source/data/notice consolidation,
  hash/provenance verification and uploaded release checks.
- `macos-ci-release.py`: version/classification, reviewed seed scope, current
  project sources, macOS packaging and release-environment checks.
- `build-windows-prerelease.ps1`: prepare, freeze, inventory and build Windows NSIS.
- `verify-macos-dmg.sh` and `macos-release.py`: mounted DMG and source/bundle checks.
- `verify-windows-installer-terms.ps1`, `verify-windows-install.ps1`,
  `verify-windows-ui.ps1` and `smoke-windows-install.py`: exact installed verification.

`release_api.py` supplies shared GitHub API requests and candidate-file validation.
Its retired private-draft staging CLI is
removed. `release_dictionaries.py` supplies safe redirects and hash-checked
dictionary restoration; the old develop-only downloader is removed. Current
private seed identities and download checks live in `desktop_release.py`.

## Windows build, runtime and source dependencies

The `windows_*` component scripts prepare CPython, minimal OpenCV, Sudachi,
NSIS, the source WebView loader, canonical VC inputs, export bindings, native
preferred sources and full notices. Their manifests/locks remain under `docs/`.
The C++ WebView adapter/probe and native probes are part of those build checks.

`onnx_detector.py`,
`onnx_runtime.py` and `onnx_generation.py` are imported by the packaged
Windows service. `prepare_windows_onnx.py`, `export_onnx_models.py` and
`verify_onnx_models.py` perform its current preparation/export/parity checks.
`onnx-probe-inputs.json` remains an exact input manifest. These are required code,
not obsolete workflow tools. The two PNG fixtures are synthetic OCR tests.

Preparation, export, parity and inference scripts now use names that describe
their current functions. Backend imports, source recipes and exporter hash checks
use those paths. The pinned input manifest retains its existing name.

## Manual rebuild and licence maintenance

- `build-macos-prerelease.sh`, `verify-python-release-lock.py`,
  `build-opencv-macos.py`, `opencv_release.py`, `generate-macos-notices.py`,
  `verify-macos-bundle.py` and `smoke-macos-bundle.py` support macOS runtime
  preparation and verification. The main workflow reuses the reviewed runtime;
  dependency/OCR changes require a freshly reviewed seed.
- `prepare-macos-sources.py` is the documented source collector/assembler.
- `create-manga-ocr-warmup.py` supplies a synthetic example instead of manga artwork.
- `build-geos-windows.py` and `geos-windows-probe.py` remain for compatible GEOS
  replacement/rebuilds; see [replacement instructions](../docs/windows-native-replacement.md).
- `sync-upstream-notices.py` is manual notice research/maintenance. It resolves
  upstream default-branch commits when explicitly run; newly collected texts
  require exact-version review before replacing reviewed notices. Normal builds
  use checked-in notice records and do not call this script.

## Retired tools

The completed v0.1.0 recovery, the fixed old private GEOS installer experiment
and initial VC inventory audit are removed, along with tests solely for those
retired paths. Current publisher, candidate, native ABI, source safety and
dictionary hash/redirect tests remain. Legacy 17-file delivery verification is
still exercised by `test_desktop_release.py`.

Historical code is recoverable at Git commit `843869a`. Current installer/runtime
code, source manifests, original licence notices and published assets are preserved.
