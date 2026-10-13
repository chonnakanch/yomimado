import { postServiceJson, requestService } from "./service-client";
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

function isSavedWord(value: unknown): value is SavedWord {
  if (!value || typeof value !== "object") return false;
  const word = value as Record<string, unknown>;
  return (
    typeof word.id === "number" &&
    Number.isSafeInteger(word.id) &&
    word.id > 0 &&
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
  const result = await postServiceJson(
    "/api/v1/vocabulary",
    "Vocabulary service",
    input,
  );
  if (!isSavedWord(result))
    throw new Error("Vocabulary service returned invalid data");
  return result;
}

export async function listVocabularyWords(): Promise<SavedWord[]> {
  const response = await requestService(
    "/api/v1/vocabulary",
    "Vocabulary service",
  );
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
  await requestService(`/api/v1/vocabulary/${id}`, "Vocabulary service", {
    method: "DELETE",
  });
}
