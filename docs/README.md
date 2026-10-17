# Documentation

## Using and developing YomiMado

- [Reading guide](usage.md): capture, page scan, learning popups and saved entries.
- [Development setup](development.md): local service, models, dictionaries and diagnostics.
- [Script roles](../scripts/README.md): release entrypoints, runtime dependencies and manual rebuild tools.
- [Implementation plan](implementation-plan.md): completed milestone and current maintenance scope.
- [Code quality review](code-review-2026-10-13.md): fixed boundary/state issues, duplication and refactor follow-ups.
- [Redesign quality review](ui-redesign-review.md) and [Windows UI checklist](ui-redesign-windows-checklist.md): current source checks and remaining interactive acceptance.
- [Security review](security-review-2026-10-13.md): browser/input guards, dependency advisories and remaining runtime work.
- [Product and architecture design](initial-design.md): domain boundaries and coordinate rules.
- [App resources and data flow](app-resources.md): how detection, recognition, tokenizer dictionaries, learning dictionaries, translation and local storage work together.
- [Tokenizer resource investigation](tokenizer-resource-investigation.md): tested UniDic-free OCR decoding and the size/behavior tradeoff of Sudachi Small.
- [Lindera tokenizer experiment](lindera-tokenizer-experiment.md): opt-in IPADIC adapter, measured size/learning differences and reproduction commands.
- [Scan performance and accuracy](scan-performance-comparison.md): stage timings and ground-truth synthetic detection/recognition results for both tokenizers.
- [App icon](app-icon.md): the current icon's origin and generation record.
- [Dictionary updates](dictionary-updates.md): snapshot replacement and attribution.

## Releases

- [Shared release checklist](desktop-release.md): published v0.1.0 identities,
  Checks/Release workflows, future six-file delivery and protected publication.
- [Release notes template](desktop-release-notes.md): generated notes for future versions.
- [macOS release guide](macos-release.md) and [Windows release guide](windows-release.md):
  platform packaging and retained preparation evidence.
- [Verified macOS runtime seed](macos-runtime-seed.md): private input hashes,
  source-only approval, exact frozen-service verification and completed input recovery.
- [macOS installed-app record](macos-clean-mac-test.md) and
  [Windows installed-app record](windows-installed-test.md): exact tested hashes,
  owner reports, waivers and untested hardware.

The published first release is complete. Historical preparation statements in
the platform guides describe their dated candidates; the published status and
exact-installer records take precedence. New versions require their own gates.

## Required source and build records

The platform source reviews, native-library replacement instructions and runtime
records remain because they support the distributed app's exact sources,
licences and rebuild recipes. The `windows-*.json` manifests and two Cargo locks
are retained build/audit inputs; several are read directly by packaging scripts.
Keep them with the corresponding code and third-party licence texts.

Superseded release-note drafts, Microsoft terms drafts, experiment timelines,
one-time recovery instructions and retired workflow copies have been removed.
Their historical contents remain available at Git commit `2885586`, for example
`rtk git show 2885586:docs/windows-native-rebuild.md`. Existing release assets,
source manifests, original licence notices and installed-app evidence are preserved.
