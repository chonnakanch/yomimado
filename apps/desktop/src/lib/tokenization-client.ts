import { parseTextTokens } from "./token-validation";
import { postServiceJson } from "./service-client";
import type { TextToken } from "./ocr-types";

export async function requestTokenization(text: string): Promise<TextToken[]> {
  if (!text.trim()) return [];

  const result = await postServiceJson("/api/v1/tokenize", "Tokenizer", {
    text,
  });
  if (
    !result ||
    typeof result !== "object" ||
    !("sourceText" in result) ||
    result.sourceText !== text ||
    !("tokens" in result)
  ) {
    throw new Error("Tokenizer returned invalid token offsets or fields");
  }
  return parseTextTokens(result.tokens, text);
}
