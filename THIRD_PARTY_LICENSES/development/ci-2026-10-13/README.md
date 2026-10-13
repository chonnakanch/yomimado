# Test-only CI inputs — 2026-10-13

These tools run in Checks and local verification; they are not added to either
installer. They do not replace the release dependency/source/native reviews.

- `actions/cache` v4.3.0 is pinned to
  `0057852bfaa89a56745cba8c7296529d2fc39830`; its original MIT licence is retained.
- `actionlint` v1.7.7 uses the upstream Linux AMD64 archive, checked against
  SHA-256 `023070a287cd8cccd71515fedc843f1985bf96c436b7effaecce67290e7e0757`.
  Its original MIT licence is retained.
- `opencv-python-headless` 4.11.0.86 supplies synthetic image-test operations
  without desktop GUI dependencies. Its wheel metadata declares Apache-2.0;
  the exact Linux wheel's original `LICENSE.txt` and `LICENSE-3RD-PARTY.txt`
  are retained, including bundled-component terms. This is separate from the
  minimal OpenCV binaries used in the published app.

`sources.json` records upstream URLs, wheel/notice hashes and the cache commit.
`python-inputs.json` records the exact metadata and allowed wheel hashes for all
28 packages in `scripts/requirements-ci.txt`. Other package versions match the
existing reviewed platform inputs, whose source/notice records remain with the
release delivery. Sudachi's dictionary terms remain separate from its software
licence. The CI lock includes Ubuntu x64 and macOS Apple Silicon wheels for
Python 3.11; it contains no Torch, inference models or freezer.

The pinned fixture environment still includes versions named in the dated
security-advisory snapshot. It tests the current source against the existing
dependency baseline. It does not resolve those advisories or approve future
runtime reuse; updated release inputs and a newly reviewed macOS seed remain
required before the next release.

Original licence/notice texts are preserved verbatim, including upstream whitespace.
