import { useEffect, useRef, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import {
  requestTranslation,
  type TranslationResult,
} from "../../lib/translation-client";
import { requestTokenization } from "../../lib/tokenization-client";
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
          : "OCR text (edit if needed)"}
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
                  onClick={() => setSelectedTokenIndex(tokenIndex)}
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
