# Updating the bundled EDRDG dictionaries

YomiMado bundles JMdict (English) and KANJIDIC2 from the Electronic Dictionary
Research and Development Group (EDRDG). Its [dictionary licence](https://www.edrdg.org/edrdg/licence.html)
requires a procedure for regular updates. For the packaged app, the maintainer
checks the official files at least once a month, then publishes a refreshed app
when either file changes. Users update by installing the newer YomiMado build;
the app does not silently download or replace dictionary data.

Release checklist for the maintainer:

1. Obtain current `JMdict_e.gz` from
   <https://www.edrdg.org/pub/Nihongo/JMdict_e.gz> and `kanjidic2.xml.gz` from
   <https://www.edrdg.org/kanjidic/kanjidic2.xml.gz> into
   `services/ocr/local-dictionaries/`. Do not edit their contents.
2. Confirm both are valid gzip files and run the OCR service's dictionary tests.
3. Build the app and inspect `Resources/ocr/notices/asset-checksums.txt` for the
   exact packaged SHA-256 digests. Keep that file with the release artifact.
4. Confirm the Sources and licenses section in the app and its bundled EDRDG
   licence, CC BY-SA text, and model/dictionary credits remain accessible.
5. Smoke-test word and kanji lookup in the packaged app before replacing the
   current public download. Record the dictionary refresh date in the release
   notes, even if the file digests did not change.

If a monthly refresh cannot be completed, do not publish a new app using stale
data without reviewing the EDRDG terms. The separately imported detector ONNX
model is unaffected by dictionary updates.
