import {
  listSavedSentences,
  deleteSavedSentence,
} from "../../lib/sentence-client";
import {
  CollectionFeedback,
  SavedDate,
  useRemovalFocus,
} from "./CollectionPanel";
import { useSavedCollection } from "./useSavedCollection";

export function SavedSentencesView({ active }: { active: boolean }) {
  const collection = useSavedCollection(
    active,
    listSavedSentences,
    deleteSavedSentence,
  );
  const removeWithFocus = useRemovalFocus();
  return (
    <section
      className="library-panel"
      role="tabpanel"
      id="saved-panel-sentences"
      aria-labelledby="saved-tab-sentences"
      tabIndex={0}
      hidden={!active}
    >
      <div className="library-heading">
        <div>
          <h2>Saved sentences</h2>
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
        kind="sentences"
        loading={collection.loading}
        error={collection.error}
        empty={!collection.items.length}
        removed={collection.removed}
        onRetry={() => void collection.refresh()}
      />
      <ul className="library-list">
        {collection.items.map((sentence) => (
          <li className="library-row" key={sentence.id}>
            <div className="library-row-heading">
              <p lang="ja" className="library-sentence">
                {sentence.sourceText}
              </p>
              <button
                className="utility-button"
                data-remove
                disabled={collection.removingId !== null}
                onClick={(event) =>
                  void removeWithFocus(event.currentTarget, () =>
                    collection.remove(sentence, "Remove this saved sentence?"),
                  )
                }
                aria-label={`Remove saved sentence ${sentence.id}`}
              >
                {collection.removingId === sentence.id ? "Removing…" : "Remove"}
              </button>
            </div>
            {sentence.translatedText ? (
              <div className="library-translation">
                <span className="library-metadata">
                  Saved English translation
                </span>
                <p lang="en">{sentence.translatedText}</p>
              </div>
            ) : (
              <p className="library-metadata">No translation saved.</p>
            )}
            <details className="library-context">
              <summary>Saved date</summary>
              <SavedDate value={sentence.createdAt} />
            </details>
            {collection.removalError?.id === sentence.id && (
              <p className="library-error" role="alert">
                Could not remove this sentence:{" "}
                {collection.removalError.message} Try Remove again.
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
