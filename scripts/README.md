# Script roles

## Update the app version

From the repository root, using Python 3.11 or later:

```sh
python3 scripts/update_version.py 0.2.0 --dry-run
python3 scripts/update_version.py 0.2.0
```

On Windows, use `py -3.11` in place of `python3`. The script updates all five
files: desktop `package.json`, both app entries in `package-lock.json`,
`tauri.conf.json`, `Cargo.toml` and the local app entry in `Cargo.lock`. It preserves
dependency versions, comments and formatting, and checks every input before writing.
The existing versions must agree; mismatched or malformed inputs fail without edits.

Accepted versions are `X.Y.Z` or `X.Y.Z-alpha.N`/`beta.N`/`rc.N`, without a `v`
prefix or leading zeroes. `0.x.x` and suffixed versions are pre-releases;
`1.0.0` and later without a suffix are stable. Review and commit the resulting
diff, then use the normal protected main PR and release flow. This command makes
local file edits; it does not commit, push, create tags, build or publish.

## Preview PR-based release notes

With Python 3.11+ and authenticated GitHub CLI, preview the exact release range:

```sh
rtk python3 scripts/release_notes.py github --previous-tag v0.3.0 --revision v0.4.0 --output services/ocr/build/release-notes/0.4.0-pr-preview.json
```

This creates JSON plus a matching Markdown preview with GitHub's PR titles/numbers
and Full Changelog link. It creates no tag or release. Omit `--previous-tag` to
select the highest earlier published ancestor app version, including pre-releases
and excluding private seeds/drafts. An existing target tag must match the source.
Use new output paths and committed app metadata; GitHub CLI needs the API's
`contents: write` permission to generate content. CI saves the preview before
publication approval and verifies its SHA-256/source/version before `compose`
writes the PR list and Full Changelog as the complete public body. Installation,
model setup and source/licence guidance are in README. Verification/limitations
stay in the release checklist and downloadable metadata. There is no separate
template to maintain; the public format is documented in the
[release runbook](../docs/release-runbook.md#generate-and-review-release-notes).

For an optional complete **commit audit**, the existing pinned maintainer tool
remains separate from the app/frozen runtime:

```sh
rtk python3 scripts/release_notes.py prepare
rtk python3 scripts/release_notes.py generate --previous-tag v0.3.0 --revision v0.4.0 --output services/ocr/build/release-notes/0.4.0-commit-audit.md
```

Preparation downloads checksum-pinned git-cliff 2.14.2. Generation is offline,
checks every commit and refuses existing files. Neither command updates versions,
tags, releases or historical `CHANGELOG.md`. See [the full procedure](../docs/release-runbook.md#generate-and-review-release-notes)
and [the exact-version terms](../THIRD_PARTY_LICENSES/git-cliff/README.md).

## Current release and checks

[Checks](../.github/workflows/checks.yml) runs on main pushes, PRs into main and
manual dispatches. It runs frontend and service tests,
format/type checks, release-rule/version tests, workflow lint and macOS/Windows
native debug tests/builds in parallel. Its final `gates` job requires every job
to succeed, including every native matrix entry. `requirements-ci.txt` is the
test-only Python 3.11 environment with pinned wheel hashes; it is separate from
the frozen release inputs. Checks accesses no private seed or model weights.
[Release](../.github/workflows/release.yml) is manually dispatched on main after
Checks / gates succeeds for the selected exact commit. Main merges do not start
installer builds. Release builds both platforms and keeps one owner-approved
publisher. Its script entrypoints are:

- `desktop_release.py`: pinned input transfer, source/data/notice consolidation,
  exact-commit Checks, main protection, hash/provenance and uploaded release checks.
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

The `windows_*` component scripts prepare CPython, minimal OpenCV, Lindera,
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

`translation_component.py` verifies and separates translation model data from
generated installer resources. It creates versioned Torch/ONNX ZIPs outside the
installer and a hash-pinned `notices/translation-component.json` descriptor,
retains model terms, verifies deliberate asset omissions and rejects leftover
OCR dictionary/binding files. Exact-candidate smoke can install the component
offline with `YOMIMADO_SMOKE_TRANSLATION_ARCHIVE`. Future release delivery adds
the two component ZIPs as separate hash-bound assets; historical layouts remain
supported. See [the implementation](../docs/optional-translation-and-ocr-size.md).

`benchmark_scan_pipeline.py` times detector passes, recognition and subsequent
tokenization on generated local fixtures for both development tokenizer profiles.
It verifies OCR-output parity and scores supplied geometry/text ground truth,
including full-pipeline losses rather than only clean-crop recognition. It does
not capture user screenshots or change production behavior. See the
[speed/accuracy report](../docs/scan-performance-comparison.md).

`prepare_lindera.py --download` explicitly downloads and stages the pinned IPADIC
dictionary for development. Use `--archive` for an existing archive or `--check`
to verify staged files. Packaging also supplies `--target` and `--notices`.
Changed archives, incomplete dictionaries and unexpected members are rejected.
The default resource path is `services/ocr/local-dictionaries/lindera-ipadic`.
See the [migration report](../docs/lindera-migration.md).

`dev_lindera_service.py` starts the local service with complete
OCR/model/dictionary paths, independent of the terminal working directory. It
checks required files, enables offline model loading and uses isolated development
data. It downloads nothing; `--check` performs path validation without serving.

`benchmark_lindera_tokenizer.py` compares the Lindera/IPADIC
adapter with Sudachi Core, including source offsets, fixed learning checks,
JMdict matches, payload sizes and warm adapter timings. It downloads nothing and
keeps derived lookup data in its output directory. Optional `--sudachi-small`
adds the hash-verified Small 20250515 dictionary to the same-corpus comparison;
see the [SudachiPy investigation](../docs/sudachipy-investigation.md). The strict
`--require-learning-parity` mode currently fails the whole-word compatibility
check documented in [the experiment](../docs/lindera-tokenizer-experiment.md).

`compare_tokenizer_candidates.py` covers every previously suggested engine using
seven pinned local profiles: Core, Small, Lindera/IPADIC, MeCab/IPADIC,
MeCab/UniDic Lite and Vaporetto kana/pronunciation models. It preserves unknown
fields as fallbacks, separates missing base forms from reading compatibility,
validates source offsets and retains all timing samples. It downloads nothing
and registers no production providers. See [the comparison](../docs/tokenizer-candidate-comparison.md)
for optional isolated inputs and reproduction.

`investigate_tokenizer_resources.py` is an offline, source-only diagnostic, not
an imported runtime module or release gate. It compares existing OCR tokenization
with a decoding configuration that avoids UniDic/Fugashi, runs synthetic OCR and
Sudachi checks in isolated workers, and optionally compares an explicitly supplied
Sudachi Small dictionary. It does not download inputs or modify model/runtime
files. See [the investigation and reproduction command](../docs/tokenizer-resource-investigation.md).

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
