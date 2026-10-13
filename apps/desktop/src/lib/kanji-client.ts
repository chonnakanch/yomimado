import { postServiceJson } from "./service-client";
export interface KanjiEntry {
  character: string;
  onReadings: string[];
  kunReadings: string[];
  meanings: string[];
}

export interface KanjiExample {
  expression: string;
  reading: string;
  meanings: string[];
}

function validateCharacter(character: string) {
  if (
    Array.from(character).length !== 1 ||
    !/\p{Script=Han}/u.test(character)
  ) {
    throw new Error("Select one kanji character");
  }
}

export async function requestKanji(character: string): Promise<KanjiEntry> {
  validateCharacter(character);
  const result = await postServiceJson("/api/v1/kanji", "Kanji lookup", {
    character,
  });
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

export async function requestKanjiExamples(
  character: string,
  excludeWord: string,
): Promise<KanjiExample[]> {
  validateCharacter(character);
  const result = await postServiceJson(
    "/api/v1/kanji/examples",
    "Kanji examples",
    { character, excludeWord },
  );
  if (
    !result ||
    typeof result !== "object" ||
    !("examples" in result) ||
    !Array.isArray(result.examples) ||
    !result.examples.every(
      (example: unknown) =>
        !!example &&
        typeof example === "object" &&
        "expression" in example &&
        typeof example.expression === "string" &&
        "reading" in example &&
        typeof example.reading === "string" &&
        "meanings" in example &&
        Array.isArray(example.meanings) &&
        example.meanings.every(
          (meaning: unknown) => typeof meaning === "string",
        ),
    )
  ) {
    throw new Error("Kanji examples returned invalid data");
  }
  return result.examples as KanjiExample[];
}
