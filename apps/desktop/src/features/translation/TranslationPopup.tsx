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
          setTokenError(null);
          setTokenLoading(false);
        }}
      />
      <div className="tokenization-heading">
        <span className="translation-caption">Words and readings</span>
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
            Press Analyze words to inspect this text.
          </p>
        )}
        {tokens?.map((token, index) => (
          <div className="tokenization-token" key={`${token.start}-${index}`}>
            <ruby lang="ja">
              {token.surface}
              <rt>{token.reading}</rt>
            </ruby>
            <small>Base: {token.dictionaryForm}</small>
            <small>POS: {token.partOfSpeech}</small>
          </div>
        ))}
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
