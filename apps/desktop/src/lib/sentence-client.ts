export interface SaveSentenceInput {
  sourceText: string;
  translatedText?: string;
}

export interface SavedSentence {
  id: number;
  sourceText: string;
  translatedText: string | null;
  createdAt: string;
}

const SERVICE_URL = import.meta.env.VITE_OCR_URL ?? "http://127.0.0.1:8765";

async function errorMessage(response: Response): Promise<string> {
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
  } | null;
  return body?.detail ?? `Sentence service returned ${response.status}`;
}

function isSavedSentence(value: unknown): value is SavedSentence {
  if (!value || typeof value !== "object") return false;
  const sentence = value as Record<string, unknown>;
  return (
    typeof sentence.id === "number" &&
    Number.isSafeInteger(sentence.id) &&
    sentence.id > 0 &&
    typeof sentence.sourceText === "string" &&
    (sentence.translatedText === null ||
      typeof sentence.translatedText === "string") &&
    typeof sentence.createdAt === "string"
  );
}

export async function saveSentence(
  input: SaveSentenceInput,
): Promise<SavedSentence> {
  const response = await fetch(`${SERVICE_URL}/api/v1/sentences`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  const result: unknown = await response.json();
  if (!isSavedSentence(result))
    throw new Error("Sentence service returned invalid data");
  return result;
}

export async function listSavedSentences(): Promise<SavedSentence[]> {
  const response = await fetch(`${SERVICE_URL}/api/v1/sentences`);
  if (!response.ok) throw new Error(await errorMessage(response));
  const result: unknown = await response.json();
  if (
    !result ||
    typeof result !== "object" ||
    !("sentences" in result) ||
    !Array.isArray(result.sentences) ||
    !result.sentences.every(isSavedSentence)
  ) {
    throw new Error("Sentence service returned invalid data");
  }
  return result.sentences;
}

export async function deleteSavedSentence(id: number): Promise<void> {
  if (!Number.isSafeInteger(id) || id < 1)
    throw new Error("Invalid saved sentence ID");
  const response = await fetch(`${SERVICE_URL}/api/v1/sentences/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error(await errorMessage(response));
}
