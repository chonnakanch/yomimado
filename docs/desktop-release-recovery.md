# Recover the tested v0.1.0 draft

On 2026-10-12 the owner approved publication in run `38201230907`. Its
publisher verifies the exact combined files, main protection and environment,
creates `v0.1.0` at `5159473da21c952f1a4dc87c457bba82edf5edde`, and uploads
all 17 delivery files. It then fails with HTTP 404 at the draft-by-tag lookup.
The owner-visible draft is `untagged-e301a488f7929f16aa3d`, titled
**YomiMado v0.1.0**, with pre-release selected. The release remains private; the version tag already exists.

The normal publisher repair resolves drafts from the complete release listing,
rejects ambiguous/wrong-target/wrong-classification drafts, retrieves them by
numeric release ID and verifies all uploaded digests before publication.
Post-publication identity/digests are also checked by ID. Do not rerun the
unchanged old publisher: it refuses the existing tag, and its code still uses
the failing draft endpoint. Do not delete/move the tag or replace the assets.

## Preserve the passed installers

The one-candidate **Desktop release resume verified draft** workflow does not
build or upload installers. It downloads the exact original combined Actions
artifact `11726850805` from run `38201230907`, requires its GitHub ZIP digest
`a6eec1b72e614ba45d30e9fe0651bb079b6266df0db5a4871e55bc896a5be91a`, and
verifies the pinned combined-record hash and all 17 exact files. Installer hashes:

- macOS: `9d2999ae49b1756d23e62e6b703284e1d5c87898dc187757dfa3d881b8b28977`.
- Windows: `a8275246dc07a30f84a2109530bd68c3c0cceeed2556ce27fb09681d3a404602`.

The owner has confirmed these exact installers' local gates; no retest or
runtime replacement is proposed. Fresh-Mac testing remains waived and AMD,
additional/mixed-scale/left-of-primary monitors and missing-WebView2 clean
machines remain untested. Full source-only rebuilding remains unverified.

The recovery runs only on protected default `main`. Its reviewed main commit
must descend from the original source and differ only in the explicit release
repair file list in `desktop_release_recovery.py`; app/runtime, version, unrelated
cleanup and licence changes are rejected. Its new main source is the repair
executor only. The existing release tag, installers, project/source delivery
and provenance stay bound to the original tested `5159473` source.

The read-only verification job completes before a fresh owner review in the
unchanged `macos-release` environment. The serialized publisher checks current
main/protections, original run/build gates, artifact retention/digest, existing
exact-source tag and the unique draft by ID. After every uploaded file's GitHub
digest/state verifies, its sole mutation is `PATCH /releases/<id>` with
`draft=false`. It creates no tag, uploads/replaces/deletes no assets and alters
no protection or credentials. The final report confirms published identity and
all digests. A failed verification cannot reach that mutation.

## Owner steps after the repair PR is verified

1. Separately authorize the focused repair PR. Earlier merge authorization
   covers PR #3 only. The repair branch excludes unrelated develop cleanup and
   test-record commits; the strict recovery scope rejects their inclusion.
2. Merge through main's required checks. The normal main release workflow will
   refuse the already-existing incomplete tag; this is intentional. Use the
   dedicated recovery instead of rebuilding or deleting the tag.
3. Run **Desktop release resume verified draft**, selecting `main`. No new
   secret or personal token is needed. Its read-only candidate gate must pass.
4. Review that recovery's exact source and installer summary, then approve its
   **macos-release** deployment yourself. This authorizes public publication of
   the unchanged tested draft. The agent does not supply this owner review.
5. Verify the public pre-release has both installers and all 17 uploaded assets,
   with the original commit and hashes. Preserve the original failed-run record.

If the artifact expires, scope changes, draft/assets differ or the existing tag
moves, stop and investigate; do not broaden this pinned recovery or silently
repair state. This is a recovery for one known retained candidate, not a general
stale-candidate publication mechanism.

Local validation: **233 develop tests and 231 isolated-main release-tool tests
pass**, including actual normal
publisher shell rehearsals with draft-by-tag HTTP 404, stable/pre-release
classification, and the recovery rejection/single-mutation tests. Ruff
(Python 3.11), formatting and actionlint pass. Hosted recovery verification
and the new owner deployment review remain pending.
