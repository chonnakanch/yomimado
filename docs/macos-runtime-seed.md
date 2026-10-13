# Prepared macOS runtime seed

Refreshed **2026-10-13** from clean source
`42edd4e3d05af293d53d9e0036a81e9586b2bfd8`. This prepared private CI input replaces the
`5120506` frozen service and contains the Python security, translation/cache and
capture-bound fixes merged through PR #5. Its app metadata still says `0.1.0`;
the output release version comes from the merged app metadata.

Private draft: [Reviewed macOS runtime seed 42edd4e — CI input only](https://github.com/chonnakanch/yomimado/releases/tag/untagged-54d0249bb3cbf06646e4).
Input label: `macos-reviewed-seed-42edd4e`. Keep it unpublished.

**Activation is blocked by upload.** The isolated browser reports
`AttachmentUploadError: App assets attachment upload failed: storage request`.
The three-file upload and a separate notices-only retry both fail. The draft
contains metadata but no assets. Existing live pins still select `5120506`;
the verified replacement patch is retained locally as `seed-pin-update.patch`.
The owner sees GitHub's generic error, “Something went really wrong, and we
can't process that file.” The old macOS and Windows input drafts are also absent.
The approved replacement's three local files remain intact.

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
- [ ] Verify the three uploaded GitHub hashes before committing the new pins.

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
  tests, Python lint/format and actionlint; it is held until actual uploads verify.

Owner API upload step, bypassing the failed browser upload:

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

Authenticated upload remains untested because no local API credential is
configured. GitHub's status page reported no current incident and both official
API hosts passed credential-free TLS checks; neither proves that uploads will
succeed. A matching existing repository-only token can be entered at the local
prompt without changing permissions. Manual browser upload remains an alternative
if its storage failure resolves; keep both inputs unpublished.

Then verify `uploaded-inputs.json` and GitHub's four uploaded hashes, apply the
combined prepared pin patch, rerun checks, commit/push and integrate through
protected main. The patch updates the macOS seed revision, label, three hashes
and source archive paths together, plus the repacked Windows outer hash. Until
then, main's old runtime-reuse preflight continues to reject the changed service;
rerunning the old release job cannot resolve it.

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
