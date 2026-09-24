export interface TranslationResult {
  sourceText: string;
  translatedText: string;
  provider: string;
  cached: boolean;
}

const SERVICE_URL = import.meta.env.VITE_OCR_URL ?? "http://127.0.0.1:8765";

export async function requestTranslation(
  text: string,
): Promise<TranslationResult> {
  const source = text.trim();
  if (!source) throw new Error("Enter Japanese text before translating.");

  const response = await fetch(`${SERVICE_URL}/api/v1/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: source }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(
      body?.detail ?? `Translation service returned ${response.status}`,
    );
  }
  const result: unknown = await response.json();
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
