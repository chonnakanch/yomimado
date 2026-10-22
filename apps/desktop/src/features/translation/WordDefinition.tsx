import type { TextToken } from "../../lib/ocr-types";
import type { WordEntry } from "../../lib/word-client";
import { hiraganaReading } from "./ClickableSentence";
import { JlptBadge } from "../jlpt/JlptBadge";
import { useJlptVisible } from "../jlpt/preference";
import { ConjugationExplanation } from "./ConjugationExplanation";
import type { ConjugationAnalysis } from "./conjugation";
import { PopupIcon } from "./PopupIcon";

export function WordDefinition({
  token,
  manualSelection = false,
  conjugation = null,
  entries,
  loading,
  error,
  saving,
  savedIndex,
  saveError,
  onSave,
  onRetry,
}: {
  token: TextToken;
  manualSelection?: boolean;
  conjugation?: ConjugationAnalysis | null;
  entries: WordEntry[] | null;
  loading: boolean;
  error: string | null;
  saving: boolean;
  savedIndex: number | null;
  saveError: string | null;
  onSave: (entry: WordEntry | null, index: number) => void;
  onRetry: () => void;
}) {
  const showJlpt = useJlptVisible();
  const saveButton = (entry: WordEntry, index: number) => (
    <button
      type="button"
      className={`utility-button save-word-button${savedIndex === index ? " is-saved" : ""}`}
      disabled={saving || savedIndex === index}
      aria-busy={saving}
      onClick={() => onSave(entry, index)}
    >
      <PopupIcon name={saving ? "loading" : "bookmark"} />
      {savedIndex === index ? "Saved" : saving ? "Saving…" : "Save word"}
    </button>
  );
  const entryView = (entry: WordEntry, index: number) => (
    <div
      className="word-entry"
      key={`${entry.expression}-${entry.reading}-${index}`}
    >
      <div className="dictionary-match" lang="ja">
        <strong>{entry.expression}</strong>
        <span>{hiraganaReading(entry.reading)}</span>
        {showJlpt && (
          <JlptBadge expression={entry.expression} reading={entry.reading} />
        )}
      </div>
      {entry.match === "dictionaryForm" && (
        <p className="popup-metadata">Matched base form</p>
      )}
      {entry.match === "surface" && token.reading && !entry.readingMatch && (
        <p className="popup-metadata">
          Reading differs from the selected token; check this sense.
        </p>
      )}
      {entry.senses.some((sense) => sense.glosses.length > 0) ? (
        <ol>
          {entry.senses.map((sense, senseIndex) => (
            <li key={senseIndex}>
              {sense.glosses.join("; ") || "No English meaning listed."}
            </li>
          ))}
        </ol>
      ) : (
        <p>No English meanings listed for this entry.</p>
      )}
      {index > 0 && saveButton(entry, index)}
    </div>
  );
  return (
    <section className="word-definition" aria-label="Selected word">
      <div className="word-heading">
        <div className="word-heading-text">
          <h2 className="selected-word" lang="ja">
            {token.surface}
          </h2>
          <p className="selected-reading" lang="ja">
            {hiraganaReading(
              manualSelection ? (entries?.[0]?.reading ?? "") : token.reading,
            ) || (manualSelection ? "" : "Reading unavailable")}
          </p>
        </div>
        {entries && entries.length > 0 && saveButton(entries[0], 0)}
      </div>
      {manualSelection ? (
        <p className="popup-metadata popup-badge">Manual selection</p>
      ) : (
        <>
          <dl className="word-metadata">
            <div>
              <dt>Base form</dt>
              <dd lang="ja">{token.dictionaryForm}</dd>
            </div>
            <div>
              <dt>Token POS</dt>
              <dd lang="ja">{token.partOfSpeech || "Not listed"}</dd>
            </div>
          </dl>
        </>
      )}
      <ConjugationExplanation analysis={conjugation} />
      {loading && <p role="status">Looking up word…</p>}
      {error && (
        <div role="alert">
          <p className="translation-error">{error}</p>
          <button className="utility-button" onClick={onRetry}>
            Retry word lookup
          </button>
        </div>
      )}
      {entries?.length === 0 && (
        <p>
          {manualSelection
            ? "No JMdict entry found for this selection. Adjust the selection and try again."
            : "No JMdict entry found for this word or base form."}
        </p>
      )}
      {(entries?.length === 0 || error) && (
        <button
          className={`utility-button save-word-button${savedIndex === -1 ? " is-saved" : ""}`}
          disabled={saving || savedIndex === -1}
          onClick={() => onSave(null, -1)}
        >
          <PopupIcon name={saving ? "loading" : "bookmark"} />
          {savedIndex === -1
            ? "Saved without meaning"
            : saving
              ? "Saving…"
              : "Save without meaning"}
        </button>
      )}
      {entries && entries.length > 0 && (
        <>
          {entryView(entries[0], 0)}
          {entries.length > 1 && (
            <details className="popup-disclosure alternative-matches">
              <summary>
                Alternative dictionary matches ({entries.length - 1})
              </summary>
              {entries
                .slice(1)
                .map((entry, index) => entryView(entry, index + 1))}
            </details>
          )}
          <p className="popup-attribution">
            Possible dictionary senses, not a context-specific translation.
            Source:{" "}
            <a
              href="https://www.edrdg.org/wiki/JMdict-EDICT_Dictionary_Project.html"
              target="_blank"
              rel="noreferrer"
            >
              JMdict (EDRDG)
            </a>{" "}
            · CC BY-SA 4.0
          </p>
        </>
      )}
      {saveError && (
        <p className="translation-error" role="alert">
          {saveError}
        </p>
      )}
      {manualSelection && (
        <p className="popup-metadata">
          Switch to Words to go back to the original split.
        </p>
      )}
      <span className="visually-hidden" role="status">
        {savedIndex !== null ? "Word saved locally." : ""}
      </span>
    </section>
  );
}
