// This is only an invalidation signal. Saved text stays in the local database.
export const vocabularyRevisionKey = "yomimado.vocabulary.revision.v1";
export const vocabularyChangedEvent = "yomimado-vocabulary-changed";

export function notifyVocabularyChanged(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(vocabularyRevisionKey, crypto.randomUUID());
  } catch {
    // Same-window notifications and refresh-on-focus still work without storage.
  }
  window.dispatchEvent(new Event(vocabularyChangedEvent));
}
