# Bundled model and dictionary notices

The first macOS package uses the following assets. Their exact file SHA-256
digests are recorded in `asset-checksums.txt` alongside the packaged app. They
are not covered by YomiMado's GPL-3.0-only source licence.

| Asset | Source and revision | Terms |
| --- | --- | --- |
| Manga OCR model | [kha-white/manga-ocr-base](https://huggingface.co/kha-white/manga-ocr-base/tree/aa6573bd10b0d446cbf622e29c3e084914df9741), revision `aa6573bd10b0d446cbf622e29c3e084914df9741` | Model card identifies Apache-2.0; see `assets/Apache-2.0.txt` and `assets/manga-ocr-model-card.md`. |
| Japanese–English translation model | [Helsinki-NLP/opus-mt-ja-en](https://huggingface.co/Helsinki-NLP/opus-mt-ja-en), weights from revision `0770961a39ba6bd66305b149c3f4110bcafca2e6` | Model card identifies Apache-2.0; see `assets/Apache-2.0.txt` and the bundled model README. |
| JMdict English | [EDRDG JMdict-EDICT project](https://www.edrdg.org/wiki/JMdict-EDICT_Dictionary_Project.html) and [download](https://www.edrdg.org/pub/Nihongo/JMdict_e.gz) | Copyright James William Breen and EDRDG; CC BY-SA 4.0 and EDRDG dictionary licence. See `assets/EDRDG-dictionary-licence.html` and `assets/CC-BY-SA-4.0.txt`. |
| KANJIDIC2 | [EDRDG KANJIDIC project](https://www.edrdg.org/wiki/KANJIDIC_Project.html) and [download](https://www.edrdg.org/kanjidic/kanjidic2.xml.gz) | Copyright James William Breen and EDRDG, with additional credited contributors; CC BY-SA 4.0 and the EDRDG dictionary licence, including its KANJIDIC2 conditions. See the same licence files above. |
| Sudachi core dictionary | [SudachiDict-core](https://pypi.org/project/sudachidict-core/20250515/) version `20250515` | Apache-2.0; its package licence is in `THIRD_PARTY_SOFTWARE.md`. |

The detector's `comictextdetector.pt.onnx` weights are **not bundled**. Users
obtain them from the original publisher and import them into their own local
app data. The detector source is GPL-3.0 and is included in the package with
its own `LICENSE` file. See `MODEL_CREDITS.md` for creator attribution.

The EDRDG data is bundled without modification. We refresh the dictionary
files as described in [the update procedure](dictionary-updates.md)
and do not claim copyright over the dictionary content.
