import type { TextToken } from "../../lib/ocr-types";
import type { SavedWord } from "../../lib/vocabulary-client";
import { explainConjugation } from "./conjugation";

export function savedWordTokenIndexes(
  source: string,
  tokens: TextToken[],
  words: SavedWord[],
): ReadonlySet<number> {
  // Dictionary spelling is the collection's marker identity, independent of
  // source sentence, selected dictionary sense, and the encountered inflection.
  const spellings = new Set(
    words.map((word) => word.dictionaryForm || word.surface).filter(Boolean),
  );
  const highlighted = new Set<number>();
  if (!spellings.size) return highlighted;
  const maxLength = [...spellings].reduce(
    (length, spelling) => Math.max(length, Array.from(spelling).length),
    0,
  );
  const characters = Array.from(source);
  tokens.forEach((token, index) => {
    if (spellings.has(token.dictionaryForm || token.surface)) {
      highlighted.add(index);
      const conjugation = explainConjugation(source, tokens, token, false);
      if (conjugation?.status === "supported") {
        const end = token.start + Array.from(conjugation.surface).length;
        for (let next = index + 1; next < tokens.length; next++) {
          if (tokens[next].end > end) break;
          highlighted.add(next);
        }
      }
    }
    // Manual dictionary expressions can span several automatic tokens. Only
    // exact source spans at token boundaries qualify; never mark substrings.
    for (let next = index; next < tokens.length; next++) {
      const end = tokens[next].end;
      if (end - token.start > maxLength) break;
      if (spellings.has(characters.slice(token.start, end).join("")))
        for (let matched = index; matched <= next; matched++)
          highlighted.add(matched);
    }
  });
  return highlighted;
}
