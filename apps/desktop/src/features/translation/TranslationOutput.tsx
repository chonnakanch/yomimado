import { useEffect, useRef, useState } from "react";
import type { TranslationResult } from "../../lib/translation-client";
import { PopupIcon } from "./PopupIcon";

export function TranslationOutput({
  result,
  loading,
  error,
  saved,
}: {
  result: TranslationResult | null;
  loading: boolean;
  error: string | null;
  saved: boolean;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);
  const copyRequest = useRef(0);
  useEffect(
    () => () => {
      copyRequest.current++;
    },
    [],
  );
  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 1500);
    return () => clearTimeout(timer);
  }, [copied]);
  const copy = async () => {
    if (!result) return;
    const request = ++copyRequest.current;
    setCopied(false);
    setCopyError(null);
    try {
      await navigator.clipboard.writeText(result.translatedText);
      if (request === copyRequest.current) setCopied(true);
    } catch {
      if (request === copyRequest.current)
        setCopyError(
          "Could not copy the translation. Select its text and copy it manually.",
        );
    }
  };
  return (
    <section
      className="translation-output"
      aria-label="Requested translation"
      aria-live="polite"
    >
      <div className="translation-output-heading">
        <h3>Translation</h3>
        <span className="popup-badge">Local</span>
        {result?.cached && <span className="popup-metadata">cached</span>}
        {result && (
          <div className="translation-output-actions">
            <button
              type="button"
              className={`utility-button utility-icon-button${copied ? " is-copied" : ""}`}
              aria-label={copied ? "Translation copied" : "Copy translation"}
              onClick={() => void copy()}
            >
              <PopupIcon name={copied ? "check" : "copy"} />
            </button>
            <button
              type="button"
              className="utility-button utility-icon-button"
              aria-label={collapsed ? "Show translation" : "Hide translation"}
              aria-expanded={!collapsed}
              aria-controls="translation-result-text"
              onClick={() => setCollapsed(!collapsed)}
            >
              <span
                className={collapsed ? "translation-expand-icon" : undefined}
              >
                <PopupIcon name="collapse" />
              </span>
            </button>
          </div>
        )}
      </div>
      {loading && <p role="status">Translating locally…</p>}
      {error && (
        <p className="translation-error" role="alert">
          {error}
        </p>
      )}
      {copyError && (
        <p className="translation-error" role="alert">
          {copyError}
        </p>
      )}
      {copied && (
        <span className="visually-hidden" role="status">
          Translation copied.
        </span>
      )}
      {result && (
        <div id="translation-result-text" hidden={collapsed}>
          <p lang="en">{result.translatedText}</p>
          <p className="popup-metadata translation-disclaimer">
            Machine translation.{" "}
            {saved ? "Saved locally with sentence." : "Not saved."}
          </p>
        </div>
      )}
    </section>
  );
}
