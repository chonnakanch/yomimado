export interface SaveWordInput {
  surface: string;
  reading: string;
  dictionaryForm: string;
  meanings: string[];
  sourceText: string;
}

export interface SavedWord extends SaveWordInput {
  id: number;
  createdAt: string;
}

const SERVICE_URL = import.meta.env.VITE_OCR_URL ?? "http://127.0.0.1:8765";

async function errorMessage(response: Response): Promise<string> {
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
  } | null;
  return body?.detail ?? `Vocabulary service returned ${response.status}`;
}

function isSavedWord(value: unknown): value is SavedWord {
  if (!value || typeof value !== "object") return false;
  const word = value as Record<string, unknown>;
  return (
    typeof word.id === "number" &&
    Number.isSafeInteger(word.id) &&
    typeof word.surface === "string" &&
    typeof word.reading === "string" &&
    typeof word.dictionaryForm === "string" &&
    Array.isArray(word.meanings) &&
    word.meanings.every((meaning) => typeof meaning === "string") &&
    typeof word.sourceText === "string" &&
    typeof word.createdAt === "string"
  );
}

export async function saveVocabularyWord(
  input: SaveWordInput,
): Promise<SavedWord> {
  const response = await fetch(`${SERVICE_URL}/api/v1/vocabulary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await errorMessage(response));
  const result: unknown = await response.json();
  if (!isSavedWord(result))
    throw new Error("Vocabulary service returned invalid data");
  return result;
}

export async function listVocabularyWords(): Promise<SavedWord[]> {
  const response = await fetch(`${SERVICE_URL}/api/v1/vocabulary`);
  if (!response.ok) throw new Error(await errorMessage(response));
  const result: unknown = await response.json();
  if (
    !result ||
    typeof result !== "object" ||
    !("words" in result) ||
    !Array.isArray(result.words) ||
    !result.words.every(isSavedWord)
  ) {
    throw new Error("Vocabulary service returned invalid data");
  }
  return result.words;
}

export async function deleteVocabularyWord(id: number): Promise<void> {
  if (!Number.isSafeInteger(id) || id < 1)
    throw new Error("Invalid saved word ID");
  const response = await fetch(`${SERVICE_URL}/api/v1/vocabulary/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error(await errorMessage(response));
}
