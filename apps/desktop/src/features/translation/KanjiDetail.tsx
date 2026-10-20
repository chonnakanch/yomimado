import type { TextToken } from "../../lib/ocr-types";
import type { KanjiEntry, KanjiExample } from "../../lib/kanji-client";
import { hiraganaReading } from "./ClickableSentence";

export function KanjiDetail({
  token,
  selected,
  entry,
  loading,
  error,
  examples,
  exampleLoading,
  exampleError,
  examplesOpen,
  onSelect,
  onExpand,
  onRetryExamples,
}: {
  token: TextToken;
  selected: string | null;
  entry: KanjiEntry | null;
  loading: boolean;
  error: string | null;
  examples: KanjiExample[] | null;
  exampleLoading: boolean;
  exampleError: string | null;
  examplesOpen: boolean;
  onSelect: (character: string) => void;
  onExpand: (open: boolean) => void;
  onRetryExamples: () => void;
}) {
  const characters = Array.from(
    new Set(
      Array.from(token.surface).filter((character) =>
        /\p{Script=Han}/u.test(character),
      ),
    ),
  );
  if (!characters.length) return null;
  return (
    <section className="kanji-section" aria-label="Kanji in this word">
      <h3>Kanji in this word</h3>
      <div className="kanji-choices">
        {characters.map((character) => (
          <button
            className="utility-button"
            type="button"
            key={character}
            lang="ja"
            aria-label={`Look up kanji ${character}`}
            aria-pressed={selected === character}
            onClick={() => onSelect(character)}
          >
            {character}
          </button>
        ))}
      </div>
      {loading && <p role="status">Looking up {selected}…</p>}
      {error && (
        <div role="alert">
          <p className="translation-error">{error}</p>
          <button
            className="utility-button"
            onClick={() => selected && onSelect(selected)}
          >
            Retry kanji lookup
          </button>
        </div>
      )}
      {entry && (
        <div className="kanji-detail">
          <strong className="kanji-character" lang="ja">
            {entry.character}
          </strong>
          <p>Meanings: {entry.meanings.join("; ") || "not listed"}</p>
          <dl className="word-metadata">
            <div>
              <dt>On’yomi</dt>
              <dd lang="ja">{entry.onReadings.join("、") || "not listed"}</dd>
            </div>
            <div>
              <dt>Kun’yomi</dt>
              <dd lang="ja">{entry.kunReadings.join("、") || "not listed"}</dd>
            </div>
          </dl>
          <p className="popup-metadata">
            Used here in <span lang="ja">{token.surface}</span>
            {token.reading && (
              <>
                {" "}
                (whole-word reading:{" "}
                <span lang="ja">{hiraganaReading(token.reading)}</span>)
              </>
            )}
            . Character readings are possibilities; the whole-word reading is
            not split per character.
          </p>
          <p className="popup-attribution">
            Source:{" "}
            <a
              href="https://www.edrdg.org/wiki/KANJIDIC_Project.html"
              target="_blank"
              rel="noreferrer"
            >
              KANJIDIC2 (EDRDG)
            </a>{" "}
            · CC BY-SA 4.0
          </p>
        </div>
      )}
      {selected && (
        <div className="kanji-examples popup-disclosure">
          <button
            className="disclosure-button"
            aria-label="Example compounds"
            aria-expanded={examplesOpen}
            aria-controls="example-compounds"
            onClick={() => onExpand(!examplesOpen)}
          >
            <span aria-hidden="true">{examplesOpen ? "⌄" : "›"}</span> Example
            compounds
          </button>
          {examplesOpen && (
            <div id="example-compounds">
              {exampleLoading && <p role="status">Loading compounds…</p>}
              {exampleError && (
                <div role="alert">
                  <p className="translation-error">{exampleError}</p>
                  <button className="utility-button" onClick={onRetryExamples}>
                    Retry compounds
                  </button>
                </div>
              )}
              {examples &&
                (examples.length === 0 ? (
                  <p>No short compounds found in local JMdict.</p>
                ) : (
                  <ul>
                    {examples.map((example) => (
                      <li key={`${example.expression}-${example.reading}`}>
                        <strong lang="ja">{example.expression}</strong>
                        <span className="compound-reading" lang="ja">
                          {hiraganaReading(example.reading)}
                        </span>
                        <span>
                          {example.meanings.join("; ") ||
                            "No English meaning listed."}
                        </span>
                      </li>
                    ))}
                  </ul>
                ))}
              {examples && (
                <p className="popup-attribution">
                  Short dictionary words containing{" "}
                  <span lang="ja">{selected}</span>. Source:{" "}
                  <a
                    href="https://www.edrdg.org/wiki/JMdict-EDICT_Dictionary_Project.html"
                    target="_blank"
                    rel="noreferrer"
                  >
                    JMdict (EDRDG)
                  </a>{" "}
                  · CC BY-SA 4.0
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
