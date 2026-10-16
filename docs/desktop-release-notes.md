# YomiMado VERSION — CLASSIFICATION

YomiMado (読み窓) helps Japanese learners read manga already visible on their
screen: capture a region, recognize Japanese locally, then click to view readings,
dictionary/kanji information and an on-demand local translation. Saved words,
sentences and translation cache stay on the computer.

## Changes in 0.2.1

- Fix Windows scans completing without visible or interactive OCR regions. The
  overlay now starts from the loaded capture page's app URL, with its OCR state
  available before page initialization; it never navigates from a new WebView2's
  temporary blank URL. This applies to Selected Area, Whole Screen and rescans.
- Shared publication approval uses the clearer `desktop-release` environment name
  for both platforms, with the existing reviewer and branch protections.

## Changes in 0.2.0

- Redesigned floating toolbar starts at the bottom center of the screen, with
  Selected Area, smart Whole Screen, Rescan and compact controls.
- Clearer orange OCR outlines, improved character coverage and compact capture
  guidance that stays out of the selection area.
- Read with keyboard navigates OCR regions and opens the learning popup.
- Compact dictionary/learning popup with word readings, kanji, example compounds,
  OCR correction and on-demand translation.
- Saved words and sentences share one library; Saved, Settings and Sources each
  open in their own window.
- Capture debug previews match the design; detailed hover tooltips appear only
  in debug mode. Cold-start capture and overlapping OCR requests are handled.

## Downloads and installation

Download the Apple Silicon `.dmg` for macOS or the per-user Windows 11 x64
`_x64-setup.exe`. Windows inference uses the CPU and requires no developer Python
or CUDA. Paid code signing is not used for this hobby release; macOS is ad-hoc
signed and unnotarized. Follow the operating system's per-app approval flow and
keep security protections enabled. Unexpected malware/damaged-file warnings need
investigation.

Import your own compatible detector ONNX file through model setup. Detector
weights are excluded from the installer, release assets and corresponding sources.
Windows setup requires acceptance of terms applying only to Microsoft's runtime
components; YomiMado's GPL and other open-source component rights remain intact.

Corresponding project/dependency sources, build recipes, licences, data notices
and checksums accompany both installers. Source-only rebuilding of the complete
delivery remains unverified. Hardware coverage and fresh-machine limitations are
disclosed below; a successful hosted build is separate from installed-app testing.

Only the installer for your platform is needed to run YomiMado. The combined
`YomiMado_VERSION_sources.tar.gz` contains the original macOS and Windows source
archives, Windows project sources, build recipes and exact dictionary snapshots.
Extract it, then extract the platform archives inside it; each retains its
original paths. `YomiMado_VERSION_notices.tar.gz` contains the platform notices,
native input inventory and original verification records. The single
`desktop-SHA256SUMS.txt` checks both installers, both combined archives and
`desktop-release-candidate.json`, which records provenance and original input
hashes. GitHub's automatic repository source downloads do not contain all bundled
dependency sources.
