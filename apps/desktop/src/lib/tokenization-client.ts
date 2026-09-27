import type { TextToken } from "./ocr-types";

const SERVICE_URL = import.meta.env.VITE_OCR_URL ?? "http://127.0.0.1:8765";

export async function requestTokenization(text: string): Promise<TextToken[]> {
  if (!text.trim()) return [];

  const response = await fetch(`${SERVICE_URL}/api/v1/tokenize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(body?.detail ?? `Tokenizer returned ${response.status}`);
  }

  const result: unknown = await response.json();
  // The API uses Unicode code-point offsets (Python string indices), not
  // JavaScript UTF-16 code units. Array.from keeps validation consistent.
  const characters = Array.from(text);
  if (
    !result ||
    typeof result !== "object" ||
    !("sourceText" in result) ||
    result.sourceText !== text ||
    !("tokens" in result) ||
    !Array.isArray(result.tokens) ||
    !result.tokens.every(
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
  const tokens = result.tokens as TextToken[];
  let previousEnd = 0;
  for (const token of tokens) {
    if (token.start < previousEnd) {
      throw new Error("Tokenizer returned overlapping or unordered tokens");
    }
    previousEnd = token.end;
  }
  return tokens;
}
