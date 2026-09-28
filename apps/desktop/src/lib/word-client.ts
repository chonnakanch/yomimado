import type { TextToken } from "./ocr-types";

export interface WordEntry {
  expression: string;
  reading: string;
  senses: Array<{ glosses: string[] }>;
  match: "surface" | "dictionaryForm";
  readingMatch: boolean;
  common: boolean;
}

const SERVICE_URL = import.meta.env.VITE_OCR_URL ?? "http://127.0.0.1:8765";

export async function requestWord(token: TextToken): Promise<WordEntry[]> {
  const response = await fetch(`${SERVICE_URL}/api/v1/word`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      surface: token.surface,
      dictionaryForm: token.dictionaryForm,
      reading: token.reading,
    }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(body?.detail ?? `Word lookup returned ${response.status}`);
  }
  const result: unknown = await response.json();
  if (
    !result ||
    typeof result !== "object" ||
    !("entries" in result) ||
    !Array.isArray(result.entries) ||
    !result.entries.every(
      (entry: unknown) =>
        !!entry &&
        typeof entry === "object" &&
        "expression" in entry &&
        typeof entry.expression === "string" &&
        "reading" in entry &&
        typeof entry.reading === "string" &&
        "match" in entry &&
        (entry.match === "surface" || entry.match === "dictionaryForm") &&
        "readingMatch" in entry &&
        typeof entry.readingMatch === "boolean" &&
        "common" in entry &&
        typeof entry.common === "boolean" &&
        "senses" in entry &&
        Array.isArray(entry.senses) &&
        entry.senses.every(
          (sense: unknown) =>
            !!sense &&
            typeof sense === "object" &&
            "glosses" in sense &&
            Array.isArray(sense.glosses) &&
            sense.glosses.every((gloss: unknown) => typeof gloss === "string"),
        ),
    )
  ) {
    throw new Error("Word lookup returned invalid data");
  }
  return result.entries as WordEntry[];
}
