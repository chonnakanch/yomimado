export interface KanjiEntry {
  character: string;
  onReadings: string[];
  kunReadings: string[];
  meanings: string[];
}

const SERVICE_URL = import.meta.env.VITE_OCR_URL ?? "http://127.0.0.1:8765";

export async function requestKanji(character: string): Promise<KanjiEntry> {
  if (
    Array.from(character).length !== 1 ||
    !/\p{Script=Han}/u.test(character)
  ) {
    throw new Error("Select one kanji character");
  }
  const response = await fetch(`${SERVICE_URL}/api/v1/kanji`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ character }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(body?.detail ?? `Kanji lookup returned ${response.status}`);
  }
  const result: unknown = await response.json();
  if (
    !result ||
    typeof result !== "object" ||
    !("character" in result) ||
    result.character !== character ||
    !("onReadings" in result) ||
    !Array.isArray(result.onReadings) ||
    !result.onReadings.every((item: unknown) => typeof item === "string") ||
    !("kunReadings" in result) ||
    !Array.isArray(result.kunReadings) ||
    !result.kunReadings.every((item: unknown) => typeof item === "string") ||
    !("meanings" in result) ||
    !Array.isArray(result.meanings) ||
    !result.meanings.every((item: unknown) => typeof item === "string")
  ) {
    throw new Error("Kanji lookup returned invalid data");
  }
  return result as KanjiEntry;
}
