import {
  listVocabularyWords,
  deleteVocabularyWord,
} from "../../lib/vocabulary-client";
import {
  CollectionFeedback,
  SavedDate,
  useRemovalFocus,
} from "./CollectionPanel";
import { useSavedCollection } from "./useSavedCollection";

export function SavedWordsView({ active }: { active: boolean }) {
  const collection = useSavedCollection(
    active,
    listVocabularyWords,
    deleteVocabularyWord,
  );
  const removeWithFocus = useRemovalFocus();
  return (
    <section
      className="library-panel"
      role="tabpanel"
      id="saved-panel-words"
      aria-labelledby="saved-tab-words"
      tabIndex={0}
      hidden={!active}
    >
      <div className="library-heading">
        <div>
          <h2>Saved words</h2>
          <p className="library-count">
            {collection.loading
              ? "Updating…"
              : `${collection.items.length} ${collection.error ? "shown" : "saved"}`}
          </p>
        </div>
        <button
          className="utility-button"
          data-refresh
          onClick={() => void collection.refresh()}
          disabled={collection.loading || collection.removingId !== null}
        >
          Refresh
        </button>
      </div>
      <CollectionFeedback
        kind="words"
        loading={collection.loading}
        error={collection.error}
        empty={!collection.items.length}
        removed={collection.removed}
        onRetry={() => void collection.refresh()}
      />
      <ul className="library-list">
        {collection.items.map((word) => (
          <li className="library-row" key={word.id}>
            <div className="library-row-heading">
              <div className="library-word">
                <strong lang="ja">{word.surface}</strong>
                <span
                  className="library-reading"
                  lang={word.reading ? "ja" : undefined}
                >
                  {word.reading || "Reading unavailable"}
                </span>
              </div>
              <button
                className="utility-button"
                data-remove
                disabled={collection.removingId !== null}
                onClick={(event) =>
                  void removeWithFocus(event.currentTarget, () =>
                    collection.remove(
                      word,
                      `Remove ${word.surface} from saved words?`,
                    ),
                  )
                }
                aria-label={`Remove ${word.surface}`}
              >
                {collection.removingId === word.id ? "Removing…" : "Remove"}
              </button>
            </div>
            {word.dictionaryForm && word.dictionaryForm !== word.surface && (
              <p className="library-metadata">
                Base form: <span lang="ja">{word.dictionaryForm}</span>
              </p>
            )}
            {word.meanings.length > 0 ? (
              <ol className="library-meanings">
                {word.meanings.map((meaning, index) => (
                  <li key={index}>
                    {meaning || "No dictionary meaning saved."}
                  </li>
                ))}
              </ol>
            ) : (
              <p className="library-metadata">No dictionary meaning saved.</p>
            )}
            <details className="library-context">
              <summary>Source and saved date</summary>
              <p
                lang={word.sourceText ? "ja" : undefined}
                className="library-source"
              >
                {word.sourceText || "No source sentence saved."}
              </p>
              <SavedDate value={word.createdAt} />
            </details>
            {word.meanings.length > 0 && (
              <p className="library-attribution">
                Possible dictionary senses · Source:{" "}
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
            {collection.removalError?.id === word.id && (
              <p className="library-error" role="alert">
                Could not remove this word: {collection.removalError.message}{" "}
                Try Remove again.
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
