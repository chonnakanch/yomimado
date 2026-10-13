import { postServiceJson } from "./service-client";
export interface TranslationResult {
  sourceText: string;
  translatedText: string;
  provider: string;
  cached: boolean;
}

export async function requestTranslation(
  text: string,
): Promise<TranslationResult> {
  const source = text.trim();
  if (!source) throw new Error("Enter Japanese text before translating.");

  const result = await postServiceJson(
    "/api/v1/translate",
    "Translation service",
    { text: source },
  );
  if (
    typeof result !== "object" ||
    result === null ||
    !("sourceText" in result) ||
    typeof result.sourceText !== "string" ||
    !("translatedText" in result) ||
    typeof result.translatedText !== "string" ||
    !("provider" in result) ||
    typeof result.provider !== "string" ||
    !("cached" in result) ||
    typeof result.cached !== "boolean"
  ) {
    throw new Error("Translation service returned an invalid result");
  }
  return result as TranslationResult;
}
