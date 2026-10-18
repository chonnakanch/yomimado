# Lindera and IPADIC

The source packaging recipes select `lindera==6.0.0` and the prebuilt
`lindera-ipadic-6.0.0.zip` from the
[v6.0.0 release](https://github.com/lindera/lindera/releases/tag/v6.0.0).
They replace the learning tokenizer only; OCR's UniDic is separate.

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

This records identified software/data terms and exact prebuilt input identity.
It is not a completed release-source review or a source rebuild of the wheel or
dictionary. In the v6.0.0 source, the IPADIC builder references
`mecab-ipadic-2.7.0-20250920.tar.gz`; the bundled notice describes historical
IPADIC terms. Fetching that upstream source returned HTTP 403 during investigation.
Establish the precise source-to-binary dictionary provenance and complete native
dependency/source delivery review before approving a new release. Do not treat
the old Sudachi/macOS seed approval as approval of these inputs.
