import vocabulary from "./vocabulary.json";

export type JlptLevel = "N1" | "N2" | "N3" | "N4" | "N5";
const levels: Readonly<Record<string, JlptLevel>> = vocabulary.levels as Record<
  string,
  JlptLevel
>;
export const jlptSource = vocabulary.source;

export function jlptLevel(
  expression: string,
  reading: string,
): JlptLevel | undefined {
  if (!expression || !reading) return undefined;
  const kana = reading
    .normalize("NFKC")
    .replace(/[\u30a1-\u30f6]/g, (character) =>
      String.fromCharCode(character.charCodeAt(0) - 0x60),
    );
  return levels[`${expression.normalize("NFKC")}\0${kana}`];
}
