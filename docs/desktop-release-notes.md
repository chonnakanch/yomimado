# Desktop release-note format

The Release workflow generates the GitHub release description from merged PRs
since the previous published app release. This document describes the format; it
is no longer copied as a template into public release notes.

```markdown
## What's Changed

- Descriptive PR title (#123)
- Another PR title (#124)

**Full Changelog**: https://github.com/chonnakanch/yomimado/compare/v0.4.0...v0.5.0
```

The numbers and versions above are examples. GitHub supplies actual PR titles,
authors and links. Full Changelog is the final line and includes direct commits
that have no individual PR entry.

- Installation and model setup: [README](../README.md#installation).
- Sources, licences and extraction guidance: [README](../README.md#sources-and-licenses).
- Exact-installer evidence, limitations and approval records: [release checklist](desktop-release.md).
- Download hashes and provenance: the release's `desktop-SHA256SUMS.txt` and
  `desktop-release-candidate.json` assets.
- Preview generation, hash binding and publication: [release runbook](release-runbook.md#generate-and-review-release-notes).

Publication still requires the existing source, installer, candidate and owner
approval checks. These records are maintained separately from the public PR list.
