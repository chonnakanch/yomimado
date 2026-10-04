# Model and dictionary credits

YomiMado's local manga text detector uses source from
[dmMaze/comic-text-detector](https://github.com/dmMaze/comic-text-detector)
(GPL-3.0) and the `comictextdetector.pt.onnx` model file published in the
[zyddnys/manga-image-translator beta-0.2.1 release](https://github.com/zyddnys/manga-image-translator/releases/tag/beta-0.2.1).
Credit for the detector model belongs to its creators and publishers; YomiMado
does not claim ownership of it. The release page does not explicitly state
redistribution terms for the weight file, so the current bundled build is for
private local testing only, not public distribution.

Japanese text recognition uses
[kha-white/manga-ocr-base](https://huggingface.co/kha-white/manga-ocr-base)
(model card: Apache-2.0). Optional on-demand Japanese-to-English translation
uses [Helsinki-NLP/opus-mt-ja-en](https://huggingface.co/Helsinki-NLP/opus-mt-ja-en)
(model card: Apache-2.0).

Word and kanji information comes from JMdict and KANJIDIC2, copyright James
William Breen and the Electronic Dictionary Research and Development Group,
under [CC BY-SA 4.0 and the EDRDG dictionary licence](https://www.edrdg.org/edrdg/licence.html).
Japanese tokenization uses the Sudachi core dictionary from Works Applications
(Apache-2.0).

See [README.md](README.md) for the outstanding full-bundle notices and
redistribution review.
