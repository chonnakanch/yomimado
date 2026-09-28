import { useEffect, useRef, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import {
  requestTranslation,
  type TranslationResult,
} from "../../lib/translation-client";
import { requestTokenization } from "../../lib/tokenization-client";
import {
  requestKanji,
  requestKanjiExamples,
  type KanjiEntry,
  type KanjiExample,
} from "../../lib/kanji-client";
import { requestWord, type WordEntry } from "../../lib/word-client";
import type { TextToken } from "../../lib/ocr-types";

interface PopupState {
  text: string;
  demo: boolean;
}

function isWord(token: TextToken): boolean {
  return /[\p{L}\p{N}]/u.test(token.surface);
}

function textPieces(text: string, tokens: TextToken[]) {
  const characters = Array.from(text);
  const pieces: Array<{ text: string; tokenIndex?: number }> = [];
  let cursor = 0;
  tokens.forEach((token, tokenIndex) => {
    if (token.start > cursor) {
      pieces.push({ text: characters.slice(cursor, token.start).join("") });
    }
    pieces.push({ text: token.surface, tokenIndex });
    cursor = token.end;
  });
  if (cursor < characters.length) {
    pieces.push({ text: characters.slice(cursor).join("") });
  }
  return pieces;
}

export function TranslationPopup() {
  const state = JSON.parse(
    new URLSearchParams(window.location.search).get("state") ?? "null",
  ) as PopupState | null;
  const [source, setSource] = useState(state?.demo ? "" : (state?.text ?? ""));
  const [result, setResult] = useState<TranslationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [tokens, setTokens] = useState<TextToken[] | null>(null);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [tokenLoading, setTokenLoading] = useState(false);
  const [selectedTokenIndex, setSelectedTokenIndex] = useState<number | null>(
    null,
  );
  const tokenRequestId = useRef(0);
  const wordRequestId = useRef(0);
  const [wordEntries, setWordEntries] = useState<WordEntry[] | null>(null);
  const [wordError, setWordError] = useState<string | null>(null);
  const [wordLoading, setWordLoading] = useState(false);
  const kanjiRequestId = useRef(0);
  const [selectedKanji, setSelectedKanji] = useState<string | null>(null);
  const [kanjiEntry, setKanjiEntry] = useState<KanjiEntry | null>(null);
  const [kanjiError, setKanjiError] = useState<string | null>(null);
  const [kanjiLoading, setKanjiLoading] = useState(false);
  const [kanjiExamples, setKanjiExamples] = useState<KanjiExample[] | null>(
    null,
  );
  const [exampleError, setExampleError] = useState<string | null>(null);

  const selectWord = async (tokenIndex: number) => {
    const token = tokens?.[tokenIndex];
    if (!token) return;
    const requestId = ++wordRequestId.current;
    kanjiRequestId.current++;
    setSelectedTokenIndex(tokenIndex);
    setWordEntries(null);
    setWordError(null);
    setWordLoading(true);
    setSelectedKanji(null);
    setKanjiEntry(null);
    setKanjiError(null);
    setKanjiLoading(false);
    setKanjiExamples(null);
    setExampleError(null);
    try {
      const entries = await requestWord(token);
      if (requestId === wordRequestId.current) setWordEntries(entries);
    } catch (requestError) {
      if (requestId === wordRequestId.current)
        setWordError(String(requestError).replace(/^Error: /, ""));
    } finally {
      if (requestId === wordRequestId.current) setWordLoading(false);
    }
  };

  const selectKanji = async (character: string) => {
    const requestId = ++kanjiRequestId.current;
    setSelectedKanji(character);
    setKanjiEntry(null);
    setKanjiError(null);
    setKanjiLoading(true);
    setKanjiExamples(null);
    setExampleError(null);
    const selectedWord = tokens?.[selectedTokenIndex ?? -1]?.surface ?? "";
    const [entryResult, examplesResult] = await Promise.allSettled([
      requestKanji(character),
      requestKanjiExamples(character, selectedWord),
    ]);
    if (requestId !== kanjiRequestId.current) return;
    if (entryResult.status === "fulfilled") setKanjiEntry(entryResult.value);
    else setKanjiError(String(entryResult.reason).replace(/^Error: /, ""));
    if (examplesResult.status === "fulfilled")
      setKanjiExamples(examplesResult.value);
    else setExampleError(String(examplesResult.reason).replace(/^Error: /, ""));
    setKanjiLoading(false);
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") void getCurrentWindow().close();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (!state?.text.trim() || state.demo) return;
    let cancelled = false;
    const requestId = ++tokenRequestId.current;
    setTokenLoading(true);
    void requestTokenization(state.text)
      .then((nextTokens) => {
        if (!cancelled && requestId === tokenRequestId.current) {
          setTokens(nextTokens);
          setTokenLoading(false);
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled && requestId === tokenRequestId.current) {
          setTokenError(String(requestError).replace(/^Error: /, ""));
          setTokenLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [state?.text, state?.demo]);

  if (!state) return null;

  const translate = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await requestTranslation(source));
    } catch (requestError) {
      setError(String(requestError).replace(/^Error: /, ""));
    } finally {
      setLoading(false);
    }
  };

  const analyze = async () => {
    const requestId = ++tokenRequestId.current;
    setTokenLoading(true);
    setTokens(null);
    setSelectedTokenIndex(null);
    wordRequestId.current++;
    setWordEntries(null);
    setWordError(null);
    setWordLoading(false);
    kanjiRequestId.current++;
    setSelectedKanji(null);
    setKanjiEntry(null);
    setKanjiError(null);
    setKanjiExamples(null);
    setExampleError(null);
    setTokenError(null);
    try {
      const nextTokens = await requestTokenization(source);
      if (requestId === tokenRequestId.current) setTokens(nextTokens);
    } catch (requestError) {
      if (requestId === tokenRequestId.current)
        setTokenError(String(requestError).replace(/^Error: /, ""));
    } finally {
      if (requestId === tokenRequestId.current) setTokenLoading(false);
    }
  };

  return (
    <div className="translation-popup">
      <div className="translation-heading">
        <strong>Japanese → English</strong>
        <button
          className="translation-close"
          onClick={() => void getCurrentWindow().close()}
          aria-label="Close translation"
        >
          ×
        </button>
      </div>
      <label htmlFor="translation-source">
        {state.demo
          ? "Demo: type Japanese text to test translation"
          : "OCR text"}
      </label>
      <textarea
        id="translation-source"
        lang="ja"
        value={source}
        onChange={(event) => {
          tokenRequestId.current++;
          setSource(event.target.value);
          setResult(null);
          setError(null);
          setTokens(null);
          setSelectedTokenIndex(null);
          wordRequestId.current++;
          setWordEntries(null);
          setWordError(null);
          setWordLoading(false);
          kanjiRequestId.current++;
          setSelectedKanji(null);
          setKanjiEntry(null);
          setKanjiError(null);
          setKanjiLoading(false);
          setKanjiExamples(null);
          setExampleError(null);
          setTokenError(null);
          setTokenLoading(false);
        }}
      />
      <div className="tokenization-heading">
        <span className="translation-caption">Select a word</span>
        <button
          className="analyze-button"
          onClick={() => void analyze()}
          disabled={tokenLoading || !source.trim()}
        >
          {tokenLoading ? "Analyzing…" : "Analyze words"}
        </button>
      </div>
      <div className="tokenization-output" aria-live="polite">
        {tokenError && <p className="translation-error">{tokenError}</p>}
        {tokenLoading && !tokenError && <p>Analyzing words…</p>}
        {!tokenLoading && !tokenError && tokens === null && (
          <p className="translation-hint">
            Press Analyze words after editing the text.
          </p>
        )}
        {tokens && (
          <div className="tokenization-text" lang="ja">
            {textPieces(source, tokens).map((piece, index) => {
              const tokenIndex = piece.tokenIndex;
              return tokenIndex !== undefined && isWord(tokens[tokenIndex]) ? (
                <button
                  type="button"
                  className="tokenization-word"
                  aria-pressed={selectedTokenIndex === tokenIndex}
                  onClick={() => void selectWord(tokenIndex)}
                  key={`${tokens[tokenIndex].start}-${index}`}
                >
                  {piece.text}
                </button>
              ) : (
                <span key={`plain-${index}`}>{piece.text}</span>
              );
            })}
          </div>
        )}
        {tokens && !tokens.some(isWord) && (
          <p className="translation-hint">No words found in this text.</p>
        )}
        {tokens &&
          selectedTokenIndex !== null &&
          tokens[selectedTokenIndex] && (
            <div className="tokenization-selected">
              <ruby lang="ja">
                {tokens[selectedTokenIndex].surface}
                <rt>{tokens[selectedTokenIndex].reading}</rt>
              </ruby>
              <small>Base: {tokens[selectedTokenIndex].dictionaryForm}</small>
              <small>POS: {tokens[selectedTokenIndex].partOfSpeech}</small>
              <div className="word-meanings">
                {wordLoading && <small>Looking up word…</small>}
                {wordError && (
                  <small className="translation-error">{wordError}</small>
                )}
                {wordEntries?.length === 0 && (
                  <small>
                    No JMdict entry found for this word or base form.
                  </small>
                )}
                {wordEntries?.map((entry, index) => (
                  <div
                    className="word-entry"
                    key={`${entry.expression}-${entry.reading}-${index}`}
                  >
                    <strong lang="ja">
                      {entry.expression} · {entry.reading}
                    </strong>
                    {entry.match === "dictionaryForm" && (
                      <small>Matched base form</small>
                    )}
                    {entry.match === "surface" && !entry.readingMatch && (
                      <small>
                        Reading differs from the selected token; check this
                        sense.
                      </small>
                    )}
                    <ol>
                      {entry.senses.map((sense, senseIndex) => (
                        <li key={senseIndex}>{sense.glosses.join("; ")}</li>
                      ))}
                    </ol>
                  </div>
                ))}
                {wordEntries && wordEntries.length > 0 && (
                  <small>
                    Possible dictionary senses, not a context-specific
                    translation. Source:{" "}
                    <a
                      href="https://www.edrdg.org/wiki/JMdict-EDICT_Dictionary_Project.html"
                      target="_blank"
                      rel="noreferrer"
                    >
                      JMdict (EDRDG)
                    </a>{" "}
                    · CC BY-SA 4.0
                  </small>
                )}
              </div>
              {Array.from(tokens[selectedTokenIndex].surface).some(
                (character) => /\p{Script=Han}/u.test(character),
              ) && (
                <div className="kanji-section">
                  <span className="translation-caption">
                    Kanji in this word
                  </span>
                  <div className="kanji-choices">
                    {Array.from(tokens[selectedTokenIndex].surface).map(
                      (character, index) =>
                        /\p{Script=Han}/u.test(character) && (
                          <button
                            type="button"
                            key={`${character}-${index}`}
                            aria-label={`Look up kanji ${character}`}
                            aria-pressed={selectedKanji === character}
                            onClick={() => void selectKanji(character)}
                          >
                            {character}
                          </button>
                        ),
                    )}
                  </div>
                  {kanjiLoading && <small>Looking up {selectedKanji}…</small>}
                  {kanjiError && (
                    <small className="translation-error">{kanjiError}</small>
                  )}
                  {kanjiEntry && (
                    <div className="kanji-detail">
                      <strong>{kanjiEntry.character}</strong>
                      <span>
                        Meanings:{" "}
                        {kanjiEntry.meanings.join("; ") || "not listed"}
                      </span>
                      <span>
                        On: {kanjiEntry.onReadings.join("、") || "not listed"}
                      </span>
                      <span>
                        Kun: {kanjiEntry.kunReadings.join("、") || "not listed"}
                      </span>
                      <span>
                        Used here in {tokens[selectedTokenIndex].surface}{" "}
                        (whole-word reading:{" "}
                        {tokens[selectedTokenIndex].reading}).
                      </span>
                      <span lang="ja">In this sentence: {source}</span>
                      <small>
                        Character readings are possibilities; the whole-word
                        reading is not split per character.
                      </small>
                      <small>
                        Source:{" "}
                        <a
                          href="https://www.edrdg.org/wiki/KANJIDIC_Project.html"
                          target="_blank"
                          rel="noreferrer"
                        >
                          KANJIDIC2 (EDRDG)
                        </a>{" "}
                        · CC BY-SA 4.0
                      </small>
                    </div>
                  )}
                  {exampleError && (
                    <small className="translation-error">{exampleError}</small>
                  )}
                  {kanjiExamples && (
                    <div className="kanji-examples">
                      <span className="translation-caption">
                        Example compounds
                      </span>
                      {kanjiExamples.length === 0 ? (
                        <small>No short compounds found in local JMdict.</small>
                      ) : (
                        <ul>
                          {kanjiExamples.map((example) => (
                            <li
                              key={`${example.expression}-${example.reading}`}
                            >
                              <strong lang="ja">{example.expression}</strong>{" "}
                              <span lang="ja">({example.reading})</span>
                              <span> — {example.meanings.join("; ")}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                      <small>
                        Short dictionary words containing {selectedKanji}.
                        Source:{" "}
                        <a
                          href="https://www.edrdg.org/wiki/JMdict-EDICT_Dictionary_Project.html"
                          target="_blank"
                          rel="noreferrer"
                        >
                          JMdict (EDRDG)
                        </a>{" "}
                        · CC BY-SA 4.0
                      </small>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
      </div>
      <button
        className="translate-button"
        onClick={() => void translate()}
        disabled={loading || !source.trim()}
      >
        {loading ? "Translating…" : "Translate locally"}
      </button>
      <div className="translation-output" aria-live="polite">
        {error && <p className="translation-error">{error}</p>}
        {result && (
          <>
            <span className="translation-caption">
              English{result.cached ? " · cached" : ""}
            </span>
            <p lang="en">{result.translatedText}</p>
          </>
        )}
        {!error && !result && !loading && (
          <p className="translation-hint">
            Translation starts only when you press the button.
          </p>
        )}
      </div>
    </div>
  );
}
