# Lindera/IPADIC development experiment

These are exact notices from the isolated tokenizer experiment, not an approval
to add a dependency to either released application runtime.

| Input                                  | Evidence                                                                                        |
| -------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Lindera Python 6.0.0 macOS ARM64 wheel | `lindera-LICENSE.txt`, copied from its wheel; MIT                                               |
| `lindera-ipadic-6.0.0.zip`             | `IPADIC-NOTICE.txt`, copied unchanged from the dictionary archive; retains NAIST and ICOT terms |
| Exact package/archive/file hashes      | [Experiment manifest](../../../services/ocr/lindera-experiment-inputs.json)                     |

The wheel has no Python runtime dependencies declared in its metadata and has a
Rust dependency SBOM. Its complete native/transitive source-and-notice delivery
has not been assembled or reviewed for release. The Windows x64 wheel hash is
recorded from exact-version PyPI metadata; that wheel has not been executed here.

Dictionary identity needs further source verification before distribution. The
v6.0.0 builder references `mecab-ipadic-2.7.0-20250920.tar.gz` at `Lindera.dev`,
while its shipped notice names the original `mecab-ipadic-2.7.0-20070801` data.
Both statements are preserved without claiming a verified source rebuild.
The experiment verifies the exact prebuilt archive and every loaded file.

Sources inspected:

- [Exact PyPI release](https://pypi.org/project/lindera/6.0.0/).
- [Exact dictionary release](https://github.com/lindera/lindera/releases/tag/v6.0.0).
- [Versioned builder recipe](https://github.com/lindera/lindera/blob/v6.0.0/lindera-ipadic/build.rs).

No dictionary binary or third-party wheel is committed to this repository.
