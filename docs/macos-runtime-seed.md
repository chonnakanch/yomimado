# Prepared macOS runtime seed

Refreshed **2026-10-13** from clean source
`42edd4e3d05af293d53d9e0036a81e9586b2bfd8`. This prepared private CI input replaces the
`5120506` frozen service and contains the Python security, translation/cache and
capture-bound fixes merged through PR #5. Its app metadata still says `0.1.0`;
the output release version comes from the merged app metadata.

Private draft: [Reviewed macOS runtime seed 42edd4e — CI input only](https://github.com/chonnakanch/yomimado/releases/tag/untagged-54d0249bb3cbf06646e4).
Input label: `macos-reviewed-seed-42edd4e`. Keep it unpublished.

**macOS upload verified; replacement pins activated on `develop`.** The owner
uploaded the three files through their browser. GitHub displays exactly the
SHA-256 hashes below; the saved draft label and full source target match. The
runtime-reuse preflight now passes. The isolated browser's earlier storage error
does not affect these completed uploads.

The Windows dictionary draft has been recreated, but its upload failed in the
isolated browser. The Windows outer-archive hash remains unchanged until that
asset can be verified. Integration through protected main is still pending;
neither input is published.

| Input                                   | SHA-256                                                            |
| --------------------------------------- | ------------------------------------------------------------------ |
| `YomiMado_0.1.0_aarch64.dmg`            | `5b7fd0dc412abb370c341d25d2bbb696ad54488cdc3006f3bd662dc1b6a52b8b` |
| `YomiMado_0.1.0_sources_42edd4e.tar.gz` | `3781bfa964a9a5c8362162a007323aa03bc912fdb54a6a33c72bf1769b7aa878` |
| `YomiMado_0.1.0_notices_42edd4e.tar.gz` | `c5af0d218248cb3c46bfe4ffb402e11c2a2b42045fbaf83d7c2b6f30d0045ff9` |

Sources extract to `source-delivery-42edd4e/`: all **477 entries / 75 archives**
and documented omissions are retained. The **74 dependency archives** are
unchanged; only the project archive is replaced. All archive hashes, notice paths
and preferred service sources verify. Historical content/rebuild reports describe
their original candidates; `runtime-refresh-verification.json` records this refresh.

The maintainer explicitly approved **source delivery only**, as `chonnakanch`,
on 2026-10-13. The embedded `source-delivery.json` records that scope and passes
the full source gate. It does not approve installed-app acceptance or publication.

Verified for this exact seed:

- [x] Pinned source-built Python/native environment; no Torch source rebuild.
- [x] Mounted bundle, platform, source/notices, detector-weight exclusion and all
      Mach-O/ad-hoc bundle signatures.
- [x] Frozen offline health, vertical OCR geometry, Sudachi, JMdict, KANJIDIC2,
      new translation and saved-word/sentence/cache persistence across restart.
- [x] Six modules extracted from the mounted executable match the committed
      service bytecode, including middleware and translation fixes.
- [x] Live rejection of missing client header, hostile origin/Host and oversized
      declared JSON; ordinary desktop lookup succeeds.
- [x] All **362 component records** and **123 native-library records** (114 unique
      inputs plus aliases) are byte-identical to the approved baseline.
- [x] 78 service and 229 release-tool tests; Python lint/format and actionlint.
- [x] Verify the three uploaded GitHub hashes and activate the matching macOS pins.
- [x] Runtime-reuse preflight, 44 shared-release/rule tests, lint/format and actionlint.
- [ ] Complete the private Windows dictionary upload and verify its new outer hash.
- [ ] Integrate the verified inputs through protected main's required Checks.

Private input recovery — 2026-10-13:

- The original `5120506` source and notice archives retain their exact hashes,
  but its original DMG is unavailable locally. Its generated output was replaced
  during the runtime refresh. Use this complete approved `42edd4e` seed rather
  than mixing a different DMG with the old source manifest.
- The exact Windows JMdict/KANJIDIC2 gzip files were recovered from retained
  audit data. Both match `windows-assets.json` and pass dictionary restoration.
  Their new outer archive SHA-256 is
  `077d6b93a5691a17aee7d8847b832b7c844f45b11270614b2eca50a9b35c5654`;
  it differs from the deleted outer archive. Dictionary bytes are unchanged.
- A one-off uploader, instructions and recovery evidence are retained locally
  under ignored `services/ocr/build/private-input-restoration-20261013/`.
  All four input hashes and 13 private-creation, identity/hash rejection and
  resume checks pass. The combined `pin-update.patch` passes 53 shared-release/version
  tests, Python lint/format and actionlint. The macOS part is now activated after
  upload verification; `windows-pin-update.patch` remains held separately.

Remaining owner upload step:

1. Open the [private Windows dictionary draft](https://github.com/chonnakanch/yomimado/releases/edit/untagged-a3752f5e03405f7d7a99)
   in the same signed-in browser that successfully uploaded the macOS files.
2. Remove the entry marked **Upload failed**, then attach
   `services/ocr/build/private-input-restoration-20261013/windows-dictionary-snapshots.tar.gz`
   (12,074,818 bytes). The agent left the failed entry for owner handling; no
   completed asset was deleted or overwritten.
3. Wait for upload completion and choose **Save draft**. Keep it unpublished.
   Verify GitHub's asset digest against `077d6b93…35c5654` above before activating
   the held Windows pin.

Alternative owner API uploader, retained locally:

```sh
cd /Users/chonnakan/Projects/yomimado
rtk proxy services/ocr/build/release-venv/bin/python services/ocr/build/private-input-restoration-20261013/upload_private_inputs.py --upload
```

Run this in your own interactive terminal. At its hidden prompt, use a short-lived
fine-grained GitHub token selecting only `chonnakanch/yomimado` with **Contents:
read and write**; Workflows permission is unnecessary. The owner must create or
change credentials personally. Keep the token out of chat and command arguments.
The uploader never saves it, follows redirects, publishes, creates public tags,
deletes or overwrites assets. It uses official GitHub API hosts, validates private
draft identity, reuses matching completed uploads, and requires each uploaded
asset's digest, size and state to match. Revoke a temporary token afterward.

Authenticated API upload remains untested because no local API credential is
configured. The failed Windows asset entry must be removed by the owner first;
the uploader deliberately rejects incomplete or altered existing assets. A
matching existing repository-only token can be entered at the local prompt
without changing permissions. The token is unnecessary for a successful manual
browser upload; keep both inputs unpublished.

Local `browser-verified-inputs.json` records the observed draft IDs, source targets,
three verified macOS hashes and Windows upload failure. It is separate from the
API uploader's success report. After the Windows digest verifies, apply only its
held pin patch, rerun checks and integrate through protected main. Main still
selects the old macOS runtime until that change is merged; rerunning the old job
cannot resolve it.

Local evidence is retained under ignored
`services/ocr/build/macos-runtime-refresh-42edd4e/`. The approved-source build uses
`scripts/build-macos-prerelease.sh --release`, the approved source-review directory
and the separately installed detector for smoke tests. Both archives contain the
approval manifest; the source archive also contains the exact-runtime report.

This refresh **does not patch dependency versions**. The
[security review](security-review-2026-10-13.md)'s advisory triage, including
Starlette/python-multipart, remains open. Full source-only rebuilding is unverified.
Do not describe this seed as resolving those findings.

Windows dictionary bytes and historical installer acceptance remain unchanged. New joint
installers require automated checks, exact-hash owner tests and protected
publication approval. The runtime-reuse guard remains intact; changed frozen code,
dependencies, native recipes or licence inputs require another reviewed seed.
