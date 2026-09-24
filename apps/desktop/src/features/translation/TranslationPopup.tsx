import { useEffect, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import {
  requestTranslation,
  type TranslationResult,
} from "../../lib/translation-client";

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

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") void getCurrentWindow().close();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

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
          setSource(event.target.value);
          setResult(null);
          setError(null);
        }}
      />
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
