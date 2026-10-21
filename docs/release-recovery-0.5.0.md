# Original v0.5.0 publication recovery — 2026-10-21

Original source: `8ff3be2621096a9804cc23ba33902f5aab34da55`, the merge of PR #27.
Original [Release run `39571798373`](https://github.com/chonnakanch/yomimado/actions/runs/39571798373)
has successful plan, seed-input, macOS/Windows build and combined-verification jobs.
Its GitHub run metadata identifies PR head `98e5ccf6fd546b313f7303d7bdbc11fe70b14e34`;
the combined candidate and platform records bind the actual merged source above.
Preserve both identities rather than confusing the PR head with the installer source.

## Failure and repair

The publisher was rejected before any step ran:

> Branch "refs/pull/27/merge" is not allowed to deploy to desktop-release due to environment protection rules.

The owner retried it; attempt 2 has the same rejection. Its publish job has no
steps, so neither blocked attempt creates a tag, draft or asset upload.
GitHub evaluates `pull_request` deployments against that PR merge ref. The
[documented default-branch semantics](https://github.blog/changelog/2025-11-07-actions-pull_request_target-and-environment-branch-protections-changes/)
of `pull_request_target` match the existing main-only protection.

The permanent Release repair retains all same-repository, merged, `release/*`,
base-main and exact-merge-SHA conditions. It checks out only `github.sha` from
the trusted default branch, never an unmerged head. Owner review, private-input
isolation, seed guards and main-only environment rules remain enforced.

## Pinned retained delivery

The public GitHub artifact metadata was inspected on 2026-10-21. Both artifacts
are unexpired and belong to the original run and PR head above.

| Artifact                     |          ID |         Bytes | ZIP SHA-256                                                        |
| ---------------------------- | ----------: | ------------: | ------------------------------------------------------------------ |
| `verified-desktop-candidate` | 12335661391 | 4,267,577,495 | `89a488eb607d4772149c6ad3f5bbcf1a3d7764204581c2929820dc7155665fb3` |
| `release-notes-preview`      | 12331803425 |         1,110 | `c8b6bff11e669f90d249687914f49ec77a545f25cab766b454cd753d7cf9f93c` |

The retained ZIPs expire **2026-11-04 at 09:38 and 08:52 UTC**, respectively.
Inspect live retention before dispatch; expiration requires a new investigation.
Individual release files remain below 2 GiB; the nine-file transfer ZIP is larger.

Original installer hashes reported by the successful builders:

| Installer                      | SHA-256                                                            |
| ------------------------------ | ------------------------------------------------------------------ |
| `YomiMado_0.5.0_aarch64.dmg`   | `778c865a7b95cc05becdfc6526aa492f0cf6bf41fb72841bc9bc7218e51df1f7` |
| `YomiMado_0.5.0_x64-setup.exe` | `aa69306dfab65cadf21702e2e6ad537faf725c03af36693a7e58f4be05e6e8c6` |

The candidate ZIP contains the original installers, separate macOS/Windows sources,
combined notices, two optional translation ZIPs, provenance and checksums. The
notes ZIP contains the original JSON/Markdown preview with PRs #20–#27 and the
v0.4.0 → v0.5.0 Full Changelog. Recovery preserves those bytes and their source.

## Historical bounded procedure

The following procedure describes the retired workflow in repair commit
`0d1249273c97daf8e358bc986acb9af8632ab71d`; it is no longer an active entrypoint.

1. Merge the focused repair PR through protected main after required Checks pass.
   Wait for successful exact-commit main Checks. The repair may change only the
   explicit workflow/tool/test/document paths listed in `REPAIR_FILES` in
   `scripts/desktop_release_recovery.py`; application/runtime/version changes are
   rejected. Main must still descend from the original installer source.
2. On main, manually run **Actions → Recover v0.5.0 publication → Run workflow**.
   It has no arbitrary run, ref, artifact or version inputs. The read-only verify
   job checks main/protections/gates, the original successful jobs, the publisher's
   empty steps, both fixed artifact IDs/sizes/digests and live retention. It hashes
   downloaded ZIPs before extracting only the exact flat regular-file members.
   It then verifies all candidate/source/notice hashes and the original note binding.
3. Download the original combined candidate from its retained run. Test both exact
   installers and record actual results/waivers under the existing checklists.
   Previous owner/source approvals do not establish acceptance of these hashes.
4. The owner supplies a fresh protected `desktop-release` publication review.
   The main-context publisher downloads and verifies the same pinned originals
   again. It rejects any existing v0.5.0 tag or release. Only then does it create
   the tag at the **original source**, upload the original nine files to a draft,
   verify uploaded digests/identity and recheck current main/protections before
   making that draft public.
5. Inspect final source, pre-release classification, file membership, digests and
   public notes. Record the actual recovery outcome separately. If any upload
   partially succeeds, investigate the resulting tag/draft instead of rerunning
   this path blindly. There is no overwrite, deletion or tag-moving operation.

The normal Release publisher still requires candidate source to equal current main.
This one-candidate recovery permits the separately reviewed repair-only main diff
and tags the original installer source. It is not a generic stale-source bypass.
The bounded workflow was retired after recovery; later versions use normal Release.

## Verification and retained limits

All 94 selected release-tool tests pass, with script Ruff lint/format and pinned
actionlint for all three workflows. The origin guard also passes the four live
public GitHub metadata reports fetched with TLS verification on 2026-10-21.
Local fake-API/ZIP tests exercise original-job/retention/digest rejection, raw PR
deployment refs, runtime-change scope rejection, archive traversal/duplicates/links,
candidate tampering, note-source mismatch, tag collision, changed uploads and main
advancing before publication. No recovery dispatch, installer rebuild, remote tag
creation or publication is performed during preparation.

The original builders and combined verification passed, but new owner-installed
acceptance is not recorded here. Fresh-Mac waivers and Windows hardware gaps keep
their prior scope; full filtered-source-only rebuilding remains unverified.
At preparation time, hosted recovery, downloaded ZIP byte verification and new
protected review remained pending. The outcome below supersedes that status.

## Completed recovery and retirement

[Recovery run `39587407949`](https://github.com/chonnakanch/yomimado/actions/runs/39587407949)
completed successfully on 2026-10-21 after PR #28 merged at
`6fa6a4d497d0deb92b7255907e41826bef0f60b4` and main Checks passed.
The [public v0.5.0 pre-release](https://github.com/chonnakanch/yomimado/releases/tag/v0.5.0)
identifies original source `8ff3be2621096a9804cc23ba33902f5aab34da55`.
All nine uploaded assets are present; both published installer SHA-256 values
match the original hashes above. The notes retain PRs #20–#27 and Full Changelog.
These are observed hosted results, without a new local installer/hardware test.

The cleanup removes the temporary recovery workflow, its helper, regression
suite and CI references at the owner's request after successful publication.
The permanent trusted-main trigger fix and normal **Checks** and **Release**
workflows remain. Original candidate/source hashes and historical review
limits remain recorded here; retired code remains available in Git history.
