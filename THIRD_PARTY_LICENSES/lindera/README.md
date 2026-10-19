# Lindera and IPADIC

The source packaging recipes select `lindera==6.0.0` and the prebuilt
`lindera-ipadic-6.0.0.zip` from the
[v6.0.0 release](https://github.com/lindera/lindera/releases/tag/v6.0.0).
They supply the shared reading/tokenization path; OCR no longer bundles UniDic.

- [Lindera software licence](lindera-LICENSE.txt): MIT, retained verbatim from
  the exact Python wheel.
- [IPADIC notice](IPADIC-NOTICE.txt): separate NAIST/ICOT terms, retained verbatim
  from the dictionary archive's `NOTICE.txt`. Preserve the notice within the
  dictionary as well as in packaged notices.
- [Runtime input manifest](../../services/ocr/app/tokenizer/lindera-inputs.json):
  exact wheel URLs/hashes for macOS Apple Silicon and Windows x64, dictionary
  archive and ten individual files, notice hashes and source archive hash.

The dictionary archive SHA-256 is
`8433dbbb80d7588a565fb9247c1ac7aed3ca50c7463329e495f8bd905aece356`.
The software source archive is the tagged Lindera monorepo, including its Python
binding, rather than the former separate `lindera-python` repository. Its SHA-256
is `648da7098359db82b8b70ab8f9c53245eba296d6ce586f0c4190305b187e80a1`.
The exact source was fetched and checked during migration. Packaging source
collectors retain the archive and collect locked Rust sources/notices.

## Dictionary source verification — 2026-10-19

The original investigation's HTTP 403 was resolved. The exact builder source
references `mecab-ipadic-2.7.0-20250920.tar.gz`, upstream MD5
`a95c409f12f1023fce8ef91f991ef042`. The retained original archive has SHA-256
`a7ba9f645ffe7094e56ae1c4a81d100df8fbb1e28bbe1792622e9728e162db3d`.
All nine generated dictionary files rebuild byte for byte using Lindera 6.0.0
and the metadata from its pinned software source. The tenth file, `NOTICE.txt`,
matches the notice in that source. Original dictionary `COPYING` bytes remain
in the source delivery, separately from the release notice.

Reproduce offline with the release Python environment and retained archives:

```sh
rtk services/ocr/build/release-venv/bin/python scripts/prepare_lindera.py \
  --rebuild-source /path/to/mecab-ipadic-2.7.0-20250920.tar.gz \
  --software-source /path/to/lindera-6.0.0-source.tar.gz \
  --target /new/path/to/rebuilt-ipadic
```

The command verifies both source archive hashes, rejects unsafe source paths,
requires builder 6.0.0 and checks all ten resulting hashes before exposing the
new directory. It does not overwrite an existing dictionary.

The native source delivery retains the complete monorepo and all 399 locked
registry dependencies, including optional and non-Python targets. Missing
registry notices are recovered from pinned upstream revisions; three older
crates without VCS records additionally require identical Rust source files
and package identity at the selected immutable revision. The full original
notices are included in the runtime's native notice supplement.

This is technical source/data provenance, not a native-wheel rebuild or human
release-source approval. The macOS and Windows wheels remain publisher builds;
the complete app/all-native-dependency source-only rebuild remains unverified.
The old Sudachi/macOS seed approval does not cover these changed inputs.
