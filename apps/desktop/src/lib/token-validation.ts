import type { TextToken } from "./ocr-types";

export function parseTextTokens(value: unknown, text: string): TextToken[] {
  // The API uses Unicode code-point offsets (Python string indices), not
  // JavaScript UTF-16 code units. Array.from keeps validation consistent.
  const characters = Array.from(text);
  if (
    !Array.isArray(value) ||
    !value.every(
      (token: unknown) =>
        !!token &&
        typeof token === "object" &&
        "surface" in token &&
        typeof token.surface === "string" &&
        "reading" in token &&
        typeof token.reading === "string" &&
        "dictionaryForm" in token &&
        typeof token.dictionaryForm === "string" &&
        "partOfSpeech" in token &&
        typeof token.partOfSpeech === "string" &&
        "start" in token &&
        typeof token.start === "number" &&
        Number.isInteger(token.start) &&
        token.start >= 0 &&
        "end" in token &&
        typeof token.end === "number" &&
        Number.isInteger(token.end) &&
        token.end > token.start &&
        token.end <= characters.length &&
        characters.slice(token.start, token.end).join("") === token.surface,
    )
  ) {
    throw new Error("Tokenizer returned invalid token offsets or fields");
  }
  const tokens = value as TextToken[];
  let previousEnd = 0;
  for (const token of tokens) {
    if (token.start < previousEnd) {
      throw new Error("Tokenizer returned overlapping or unordered tokens");
    }
    previousEnd = token.end;
  }
  return tokens;
}
