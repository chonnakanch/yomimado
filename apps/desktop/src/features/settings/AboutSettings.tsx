import { jlptSource } from "../jlpt/jlpt";
import jlptLicense from "../jlpt/LICENSE.txt?raw";
import "../jlpt/jlpt.css";

export function AboutSettings() {
  return (
    <div className="settings-card settings-sources">
      <h2>About / Sources</h2>
      <p>
        YomiMado <span lang="ja">読み窓</span> · Read beyond the page.
      </p>
      <p>
        OCR and dictionary lookup stay local. Translation runs only when you
        request it.
      </p>
      <h3>Sources and licenses</h3>
      <p>
        Word and kanji data: JMdict and KANJIDIC2, copyright James William Breen
        and the Electronic Dictionary Research and Development Group (EDRDG),
        licensed under CC BY-SA 4.0. See the{" "}
        <a
          href="https://www.edrdg.org/edrdg/licence.html"
          target="_blank"
          rel="noreferrer"
        >
          dictionary licence and source
        </a>
        .
      </p>
      <p>
        OCR recognition: Manga OCR by kha-white. Translation: Helsinki-NLP
        opus-mt-ja-en. Both models are identified as Apache-2.0 by their{" "}
        <a
          href="https://huggingface.co/kha-white/manga-ocr-base"
          target="_blank"
          rel="noreferrer"
        >
          Manga OCR
        </a>{" "}
        and{" "}
        <a
          href="https://huggingface.co/Helsinki-NLP/opus-mt-ja-en"
          target="_blank"
          rel="noreferrer"
        >
          translation model
        </a>{" "}
        cards. Text detection code is from{" "}
        <a
          href="https://github.com/dmMaze/comic-text-detector"
          target="_blank"
          rel="noreferrer"
        >
          comic-text-detector
        </a>
        ; detector weights are installed separately by you.
      </p>
      <p>
        Estimated JLPT vocabulary levels: Jonathan Waller's Tanos lists, adapted
        by Stephen Kraus (2021–2025), with spellings/readings from JMdict. The
        bundled adaptation is licensed under CC BY-SA 4.0. YomiMado converts it
        to an offline spelling/reading lookup table. These are community
        estimates; words absent from the dataset are left unclassified.{" "}
        <a href={jlptSource} target="_blank" rel="noreferrer">
          JLPT data source and attribution
        </a>
        .
      </p>
      <details className="jlpt-license">
        <summary>JLPT data license — CC BY-SA 4.0</summary>
        <pre>{jlptLicense}</pre>
      </details>
      <p>
        The packaged app includes additional model, dictionary, and software
        notices in its <code>ocr/notices</code> folder (inside Resources on
        macOS).
      </p>
    </div>
  );
}
