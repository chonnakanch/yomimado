import { useEffect, useState } from "react";
import {
  listVocabularyWords,
  type SavedWord,
} from "../../lib/vocabulary-client";
import {
  vocabularyChangedEvent,
  vocabularyRevisionKey,
} from "../../lib/vocabulary-events";

export function useSavedVocabulary(active: boolean) {
  const [words, setWords] = useState<SavedWord[]>([]);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    if (!active) return;
    let request = 0;
    let disposed = false;
    const refresh = async () => {
      const current = ++request;
      try {
        const next = await listVocabularyWords();
        if (disposed || current !== request) return;
        setWords(next);
        setUnavailable(false);
      } catch {
        if (disposed || current !== request) return;
        // Do not present stale saved markers as current vocabulary.
        setWords([]);
        setUnavailable(true);
      }
    };
    const update = () => void refresh();
    const onStorage = (event: StorageEvent) => {
      if (event.key === vocabularyRevisionKey || event.key === null) update();
    };
    window.addEventListener(vocabularyChangedEvent, update);
    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", update);
    update();
    return () => {
      disposed = true;
      window.removeEventListener(vocabularyChangedEvent, update);
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", update);
    };
  }, [active]);

  return { words, unavailable };
}
