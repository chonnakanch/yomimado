import type { SavedWord } from "../../lib/vocabulary-client";
import type { SavedSentence } from "../../lib/sentence-client";

// Match Japanese readings regardless of width or kana script. Source records
// stay untouched: normalization is only for comparison.
export function normalizeSavedSearch(value: string): string {
  return value
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[ァ-ヶ]/g, (kana) =>
      String.fromCharCode(kana.charCodeAt(0) - 0x60),
    );
}

function matches(query: string, fields: string[]): boolean {
  const terms = normalizeSavedSearch(query).trim().split(/\s+/).filter(Boolean);
  const searchable = fields.map(normalizeSavedSearch);
  return terms.every((term) =>
    searchable.some((field) => field.includes(term)),
  );
}

export function matchesSavedWord(word: SavedWord, query: string): boolean {
  return matches(query, [
    word.surface,
    word.reading,
    word.dictionaryForm,
    ...word.meanings,
    word.sourceText,
  ]);
}

export function matchesSavedSentence(
  sentence: SavedSentence,
  query: string,
): boolean {
  return matches(query, [sentence.sourceText, sentence.translatedText ?? ""]);
}
