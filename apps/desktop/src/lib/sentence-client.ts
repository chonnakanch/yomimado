import { postServiceJson, requestService } from "./service-client";
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
  const result = await postServiceJson(
    "/api/v1/sentences",
    "Sentence service",
    input,
  );
  if (!isSavedSentence(result))
    throw new Error("Sentence service returned invalid data");
  return result;
}

export async function listSavedSentences(): Promise<SavedSentence[]> {
  const response = await requestService(
    "/api/v1/sentences",
    "Sentence service",
  );
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
  await requestService(`/api/v1/sentences/${id}`, "Sentence service", {
    method: "DELETE",
  });
}
