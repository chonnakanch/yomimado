# macOS runtime reuse for 0.4.0 — 2026-10-20

This is a technical review of a runtime-independent frontend data addition. It
does not record new owner source approval, installer acceptance or publication
approval. The reviewed frozen service remains at
`f1b4fbaa8980ff0df0a1abf6f5a93df058f4678e`; its private draft and all four input
hashes remain those in the [seed record](macos-runtime-seed.md).

## Failure and scope

[Release 39371691358](https://github.com/chonnakanch/yomimado/actions/runs/39371691358)
at main `ce2a3dfef0738099c43058f4a867df2c122a77c1` stopped in `plan` after PR #17
merged. Neither installer builder ran. The first rejected path was
`CHANGELOG.md`; 13 additional JLPT data/notice/generator paths also fell outside
the old reuse scope. All 12 application Checks had passed because Checks did
not execute the real committed-source preflight.

Compared with the reviewed seed, `services/ocr/`, the macOS freeze and source
collection recipes, and normalized npm/Tauri/Cargo dependency/build settings are
unchanged. JLPT data is imported by React from
`apps/desktop/src/features/jlpt/vocabulary.json`; its full licence is imported as
text by `AboutSettings.tsx`. The frontend is rebuilt for every Release. The
offline generator is never imported by the frozen Python service. The two
changed top-level third-party notice documents add JLPT attribution and repair a
relative documentation link; they change no runtime dependency terms.

Consequently, rebuilding the same frozen Python service would not resolve a
runtime difference. The repair treats `CHANGELOG.md` like the existing project
documentation exception, and accepts only the exact JLPT source/data/notice and
generator bytes identified by `FRONTEND_DATA_HASHES` in
[`scripts/macos-ci-release.py`](../scripts/macos-ci-release.py). There are 15 pins:
the 13 previously rejected files plus the generated frontend table and licence.
The guard hashes Git `HEAD` bytes, including complete line endings. A later
change to any pin, an unknown third-party file, a frozen service/dependency change
or model weights still fails. No third-party directory prefix is allowlisted.

## Separate data terms and delivery

The retained [JLPT provenance](../THIRD_PARTY_LICENSES/jlpt/README.md) identifies
upstream `b062d4e38c4bdd0950ae1d4ec55f04b176182e03`, the five original banks,
8,113 spelling/reading pairs, and Jonathan Waller / Stephen Kraus / JMdict
attribution. The upstream index explicitly grants CC BY-SA 4.0 terms for the
adaptation; the full licence and input hashes are retained. The upstream README
describes Waller's original terms as CC BY without specifying a version. Its
original site was unavailable during the recorded review; that limitation is
preserved. No broader terms are inferred. The generated data retains its
CC BY-SA 4.0 identity separately from GPL-3.0-only application software.

Source preparation exports all these files inside the exact project Git archive,
and additionally copies their committed bytes into `notices/frontend-jlpt/`,
preserving repository-relative paths. `notices/frontend-data.json` and
`ci-followup.json` record the separate licence, upstream revision and every hash.
The project source entry references the added full licence. Both source manifests
carry that reference, and the matching source-delivery notices copy retains the
supplement. Existing frozen component archives, inventory hashes and original
reviewer/date/scope remain unchanged. The follow-up explicitly states that the
original seed approval is not extended to the frontend dataset; it no longer
claims every desktop licence choice is unchanged.

Windows already rebuilds the frontend and delivers its exact project source,
including the retained data and licence. Its runtime and dictionary pins remain
unchanged by this repair.

## Verification and integration

Regression tests cover acceptance of the exact dataset, all 15 hash mismatches,
committed versus dirty bytes, unknown third-party additions and changed frozen
code. Source-export tests inspect the project archive, supplement hashes, matching
manifest entries and preservation of original approval/dependency records.
Existing dependency/model/recipe rejection cases remain in the suite.

Checks now fetches full Git history in `release-tools` and runs both `plan` and
`verify-reuse` on the checked-out commit before its release-tool tests. The
existing required `gates` job depends on `release-tools`, so rejection prevents a
green gate for develop/main pushes and main PRs. This requires no private seed
access, credentials, installer build or publisher permission. On PRs the normal
checkout tests GitHub's proposed merge commit; Release rechecks the actual main
commit.

This resolves the source-level reuse blocker after the repair is committed and
integrated. Rerunning the old failed run retains its old code and will fail again.
An authorized merge of the repair must start a fresh source-bound Release. Both
new installer hashes still require the existing acceptance and protected owner
publication steps. Full source-only rebuilding and historical hardware limits
remain unverified as recorded; this repair does not claim new installer results.
