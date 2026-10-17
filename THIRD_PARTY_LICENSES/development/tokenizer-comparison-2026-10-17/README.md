# Development tokenizer comparison notices — 2026-10-17

These are exact notices retained from inspected local test inputs. They are not
additions to the application runtime or approval to distribute a new installer.
The [input manifest](../../../services/ocr/tokenizer-comparison-inputs.json)
records exact artifact URLs, hashes, versions and extracted resource hashes.

- `IPADIC-COPYING.txt`: original bytes from the dictionary in
  `ipadic-1.0.0.tar.gz`, including NAIST/ICOT terms. Only its data directory is
  loaded through the existing Fugashi binding; its packaging scripts are not run.
- `vaporetto-LICENSE-APACHE.txt` and `vaporetto-LICENSE-MIT.txt`: Python wrapper
  0.3.3 wheel, which reports native Vaporetto 0.6.5. The inspected software offers
  these alternatives. Native/transitive source delivery remains a release task.
- The two `bccwj-suw+unidic_pos+*-BSD.txt` files: the separate terms from the
  kana/pronunciation model archives in `vaporetto-models` v0.5.0. Software license
  labels are not used as a substitute for these model notices. The archives have
  no publisher checksum in the retrieved release metadata; manifest hashes
  identify the downloaded bytes, not an independent publisher signature.
- `zstandard-LICENSE.txt`: Python zstandard 0.25.0, used to decompress the models
  before loading. It is installed only in the isolated experiment target.
- Fugashi 1.5.2, its MeCab license, UniDic Lite 1.0.8 and UniDic notices: copied
  from the existing pinned development environment. Their software/data roles
  remain separate. Existing Sudachi and Lindera notices remain in their original
  release/development records.

See the [comparison report](../../../docs/tokenizer-candidate-comparison.md) for
method, results, limitations and reproduction. All native/data inputs remain in
ignored build directories; this folder retains notices only.
