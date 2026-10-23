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
import { JlptBadge } from "../jlpt/JlptBadge";
import { useJlptVisible } from "../jlpt/preference";
import { SavedSearch, NoSearchResults, useSavedQuery } from "./SavedSearch";
import { matchesSavedWord } from "./saved-search";
import { SavedBookmark } from "./SavedBookmark";

export function SavedWordsView({
  active,
  revision = 0,
}: {
  active: boolean;
  revision?: number;
}) {
  const showJlpt = useJlptVisible();
  const collection = useSavedCollection(
    active,
    listVocabularyWords,
    deleteVocabularyWord,
    revision,
  );
  const removeWithFocus = useRemovalFocus();
  const [query, setQuery] = useSavedQuery("words");
  const filtered = collection.items.filter((word) =>
    matchesSavedWord(word, query),
  );
  return (
    <section
      className="library-panel"
      role="tabpanel"
      id="saved-panel-words"
      aria-labelledby="saved-tab-words"
      tabIndex={0}
      hidden={!active}
    >
      <SavedSearch kind="words" query={query} onChange={setQuery} />
      <div className="library-heading">
        <div>
          <h2 className="visually-hidden">Saved words</h2>
          <p
            className="library-count"
            role="status"
            aria-live={active ? "polite" : "off"}
          >
            {collection.loading
              ? "Updating…"
              : query.trim()
                ? `${filtered.length} of ${collection.items.length} words`
                : `${collection.items.length} ${collection.error ? "shown" : "saved"} ${collection.items.length === 1 ? "word" : "words"}`}
          </p>
        </div>
        <div className="library-heading-actions">
          <span className="library-order">Newest first</span>
          <button
            className="utility-button"
            data-refresh
            onClick={() => void collection.refresh()}
            disabled={collection.loading || collection.removingId !== null}
          >
            Refresh
          </button>
        </div>
      </div>
      <CollectionFeedback
        kind="words"
        loading={collection.loading}
        error={collection.error}
        empty={!collection.items.length}
        removed={collection.removed}
        onRetry={() => void collection.refresh()}
      />
      {!collection.loading &&
        collection.items.length > 0 &&
        filtered.length === 0 && (
          <NoSearchResults kind="words" onClear={() => setQuery("")} />
        )}
      <ul
        className="library-list"
        id="saved-words-results"
        aria-label="Saved word entries"
      >
        {filtered.map((word) => (
          <li className="library-row" key={word.id}>
            <div className="library-entry-main">
              <div className="library-word">
                <div className="library-word-title">
                  <strong lang="ja">{word.surface}</strong>
                  <SavedBookmark />
                  {showJlpt && (
                    <JlptBadge
                      expression={word.dictionaryForm || word.surface}
                      reading={word.reading}
                    />
                  )}
                </div>
                <span
                  className="library-reading"
                  lang={word.reading ? "ja" : undefined}
                >
                  {word.reading || "Reading unavailable"}
                </span>
                {word.dictionaryForm &&
                  word.dictionaryForm !== word.surface && (
                    <p className="library-metadata">
                      Base form: <span lang="ja">{word.dictionaryForm}</span>
                    </p>
                  )}
              </div>
              <div className="library-definition-block">
                {word.meanings.length > 0 ? (
                  <ol className="library-meanings">
                    {word.meanings.map((meaning, index) => (
                      <li key={index}>
                        {meaning || "No dictionary meaning saved."}
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="library-metadata">
                    No dictionary meaning saved.
                  </p>
                )}
              </div>
            </div>
            <div className="library-row-footer">
              <details className="library-context">
                <summary>Source sentence</summary>
                <p
                  lang={word.sourceText ? "ja" : undefined}
                  className="library-source"
                >
                  {word.sourceText || "No source sentence saved."}
                </p>
                <SavedDate value={word.createdAt} />
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
              </details>
              <button
                className="utility-button library-remove"
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
