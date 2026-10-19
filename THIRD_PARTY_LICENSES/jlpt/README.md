# Offline JLPT vocabulary data

YomiMado bundles a transformed copy of
[stephenmk/yomitan-jlpt-vocab](https://github.com/stephenmk/yomitan-jlpt-vocab)
at commit `b062d4e38c4bdd0950ae1d4ec55f04b176182e03` (dataset revision
`2025.08.01.0`). It contains 8,113 spelling/reading pairs with estimated N1–N5
levels. These are community estimates, not official exam assignments; unlisted
words are not assigned a level.

## Attribution and terms

- Jonathan Waller's Tanos JLPT Resources are the original level-list source.
  The retained upstream README describes their terms as Creative Commons BY
  without specifying a version. The original site was unavailable during this
  review; no different version or broader permission is inferred.
- Stephen Kraus adapted the lists using JMdict spellings/readings. The retained
  upstream `index.json` states: © CC BY-SA 4.0 Stephen Kraus 2021–2025, and
  explicitly permits using, modifying and redistributing these files under
  Creative Commons Attribution-ShareAlike 4.0.
- JMdict is copyright James William Breen and the Electronic Dictionary Research
  and Development Group. Its separate CC BY-SA 4.0 / EDRDG terms and attribution
  remain in the existing [dictionary notices](../ASSET_NOTICES.md).
- This dataset adaptation remains **CC BY-SA 4.0**, separately from YomiMado's
  software licence. The unmodified upstream [full licence](LICENSE.txt),
  [README](UPSTREAM_README.md), and [index](source/index.json) are retained.

## Changes and reproduction

The five upstream term-meta banks are retained byte-for-byte under `source/`.
[sources.json](sources.json) pins every source, licence and attribution file by
SHA-256 and records the generated table's hash. No upstream application code,
screenshots, dictionary definitions or Anki functionality is imported.

`scripts/prepare_jlpt.py` converts the banks to a JSON spelling/reading lookup
table. Keys use NFKC normalization and hiragana-normalized readings; levels are
preserved without inference. Conflicting labels fail generation. The full
licence is copied unchanged beside the generated frontend table and embedded
in **Sources & licenses**; credit also appears in Reading settings and badge
descriptions. The runtime table is 308,630 bytes before bundling/compression.

From the repository root, run:

```sh
rtk python3 scripts/prepare_jlpt.py --check
```

Omit `--check` to reproduce the table and frontend licence from the retained
inputs. Neither command downloads anything. Runtime lookup makes no network
requests and adds no Python package, model, or service. Source updates require
an explicit review of the revision, terms, hashes and resulting labels.

Data tests verify all input hashes, all 8,113 labels, the generated hash and
full licence retention. Frontend tests check reading-sensitive matching and display behavior.
Installer acceptance and release approval remain separate from this data review.
