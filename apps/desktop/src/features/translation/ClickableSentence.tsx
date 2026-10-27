import { useMemo } from "react";
import type { TextToken } from "../../lib/ocr-types";
import type { SavedWord } from "../../lib/vocabulary-client";
import { savedWordTokenIndexes } from "./saved-word-highlights";

export function isWord(token: TextToken): boolean {
  return /[\p{L}\p{N}]/u.test(token.surface);
}

// Kana conversion is display-only. Lookups and saved records keep API readings.
export function hiraganaReading(reading: string): string {
  return reading.replace(/[\u30a1-\u30f6]/g, (character) =>
    String.fromCharCode(character.charCodeAt(0) - 0x60),
  );
}

export function textPieces(text: string, tokens: TextToken[]) {
  const characters = Array.from(text);
  const pieces: Array<{ text: string; tokenIndex?: number }> = [];
  let cursor = 0;
  tokens.forEach((token, tokenIndex) => {
    if (token.start > cursor)
      pieces.push({ text: characters.slice(cursor, token.start).join("") });
    pieces.push({ text: token.surface, tokenIndex });
    cursor = token.end;
  });
  if (cursor < characters.length)
    pieces.push({ text: characters.slice(cursor).join("") });
  return pieces;
}

export function ClickableSentence({
  source,
  tokens,
  selectedTokenIndex,
  onSelect,
  savedWords,
}: {
  source: string;
  tokens: TextToken[] | null;
  selectedTokenIndex: number | null;
  onSelect: (index: number) => void;
  savedWords: SavedWord[];
}) {
  const savedIndexes = useMemo(
    () => savedWordTokenIndexes(source, tokens ?? [], savedWords),
    [source, tokens, savedWords],
  );
  return (
    <div
      className="tokenization-text"
      lang="ja"
      aria-label="Japanese sentence"
      tabIndex={0}
    >
      {tokens
        ? textPieces(source, tokens).map((piece, index) =>
            piece.tokenIndex !== undefined &&
            isWord(tokens[piece.tokenIndex]) ? (
              <button
                type="button"
                className={`tokenization-word${savedIndexes.has(piece.tokenIndex) ? " is-saved-word" : ""}`}
                aria-label={
                  savedIndexes.has(piece.tokenIndex)
                    ? `${piece.text} (saved word)`
                    : undefined
                }
                aria-pressed={selectedTokenIndex === piece.tokenIndex}
                onClick={() => onSelect(piece.tokenIndex!)}
                key={`${tokens[piece.tokenIndex].start}-${index}`}
              >
                {piece.text}
              </button>
            ) : (
              <span key={`plain-${index}`}>{piece.text}</span>
            ),
          )
        : source}
    </div>
  );
}
