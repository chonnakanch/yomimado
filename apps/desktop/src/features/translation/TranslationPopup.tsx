import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
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
import { saveVocabularyWord } from "../../lib/vocabulary-client";
import { saveSentence } from "../../lib/sentence-client";
import type { TextToken } from "../../lib/ocr-types";
import { debugTooltip } from "../../lib/debug-mode";
import { ClickableSentence, isWord } from "./ClickableSentence";
import { WordDefinition } from "./WordDefinition";
import { KanjiDetail } from "./KanjiDetail";
import "./popup.css";

interface PopupState {
  text: string;
  demo: boolean;
  reviewReason?: string;
  approximate?: boolean;
  placement?: {
    screen: { x: number; y: number; width: number; height: number };
    anchorLeft: number;
    anchorRight: number;
    anchorTop: number;
    scaleFactor: number;
  };
}

export function TranslationPopup() {
  const [state] = useState<PopupState | null>(
    () =>
      JSON.parse(
        new URLSearchParams(window.location.search).get("state") ?? "null",
      ) as PopupState | null,
  );
  const contentRef = useRef<HTMLDivElement>(null);
  const contextRef = useRef<HTMLDivElement>(null);
  const detailsRef = useRef<HTMLDivElement>(null);
  const detailsContentRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const editButtonRef = useRef<HTMLButtonElement>(null);
  const returnEditorFocus = useRef(false);
  const [editing, setEditing] = useState(state?.demo ?? false);
  const [draft, setDraft] = useState(state?.demo ? "" : (state?.text ?? ""));
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);
  const copyRequestId = useRef(0);
  const viewQuery = useRef(window.location.search.slice(1)).current;
  const [source, setSource] = useState(state?.demo ? "" : (state?.text ?? ""));
  const [result, setResult] = useState<TranslationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const translationRequestId = useRef(0);
  const [savingSentence, setSavingSentence] = useState(false);
  const [sentenceSaved, setSentenceSaved] = useState(false);
  const [sentenceSaveError, setSentenceSaveError] = useState<string | null>(
    null,
  );
  const sentenceSaveRequestId = useRef(0);
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
  const saveRequestId = useRef(0);
  const [savingWord, setSavingWord] = useState(false);
  const [savedEntryIndex, setSavedEntryIndex] = useState<number | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const kanjiRequestId = useRef(0);
  const exampleRequestId = useRef(0);
  const [selectedKanji, setSelectedKanji] = useState<string | null>(null);
  const [kanjiEntry, setKanjiEntry] = useState<KanjiEntry | null>(null);
  const [kanjiError, setKanjiError] = useState<string | null>(null);
  const [kanjiLoading, setKanjiLoading] = useState(false);
  const [kanjiExamples, setKanjiExamples] = useState<KanjiExample[] | null>(
    null,
  );
  const [exampleError, setExampleError] = useState<string | null>(null);
  const [exampleLoading, setExampleLoading] = useState(false);
  const [examplesOpen, setExamplesOpen] = useState(false);

  const resetWordSelection = () => {
    setSelectedTokenIndex(null);
    wordRequestId.current++;
    setWordEntries(null);
    setWordError(null);
    setWordLoading(false);
    saveRequestId.current++;
    setSavingWord(false);
    setSavedEntryIndex(null);
    setSaveError(null);
    kanjiRequestId.current++;
    setSelectedKanji(null);
    setKanjiEntry(null);
    setKanjiError(null);
    setKanjiLoading(false);
    setKanjiExamples(null);
    setExampleError(null);
    exampleRequestId.current++;
    setExampleLoading(false);
    setExamplesOpen(false);
  };

  const selectWord = async (tokenIndex: number) => {
    const token = tokens?.[tokenIndex];
    if (!token) return;
    if (
      tokenIndex === selectedTokenIndex &&
      (wordLoading || wordEntries !== null)
    )
      return;
    const requestId = ++wordRequestId.current;
    kanjiRequestId.current++;
    setSelectedTokenIndex(tokenIndex);
    setWordEntries(null);
    setWordError(null);
    setWordLoading(true);
    saveRequestId.current++;
    setSavingWord(false);
    setSavedEntryIndex(null);
    setSaveError(null);
    setSelectedKanji(null);
    setKanjiEntry(null);
    setKanjiError(null);
    setKanjiLoading(false);
    setKanjiExamples(null);
    setExampleError(null);
    exampleRequestId.current++;
    setExampleLoading(false);
    setExamplesOpen(false);
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
    if (character === selectedKanji && (kanjiLoading || kanjiEntry)) return;
    const requestId = ++kanjiRequestId.current;
    setSelectedKanji(character);
    setKanjiEntry(null);
    setKanjiError(null);
    setKanjiLoading(true);
    setKanjiExamples(null);
    setExampleError(null);
    exampleRequestId.current++;
    setExampleLoading(false);
    setExamplesOpen(false);
    try {
      const entry = await requestKanji(character);
      if (requestId === kanjiRequestId.current) setKanjiEntry(entry);
    } catch (requestError) {
      if (requestId === kanjiRequestId.current)
        setKanjiError(String(requestError).replace(/^Error: /, ""));
    } finally {
      if (requestId === kanjiRequestId.current) setKanjiLoading(false);
    }
  };

  const loadExamples = async () => {
    const token = tokens?.[selectedTokenIndex ?? -1];
    if (!selectedKanji || !token || exampleLoading) return;
    const requestId = ++exampleRequestId.current;
    setExampleLoading(true);
    setExampleError(null);
    try {
      const examples = await requestKanjiExamples(selectedKanji, token.surface);
      if (requestId === exampleRequestId.current) setKanjiExamples(examples);
    } catch (requestError) {
      if (requestId === exampleRequestId.current)
        setExampleError(String(requestError).replace(/^Error: /, ""));
    } finally {
      if (requestId === exampleRequestId.current) setExampleLoading(false);
    }
  };

  const cancelEdit = () => {
    returnEditorFocus.current = true;
    setEditing(false);
    setDraft(source);
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      if (editing) {
        cancelEdit();
        return;
      }
      void invoke("close_translation_popup", {
        returnFocus: true,
        viewQuery,
      }).catch((error) => setError(`Could not close popup: ${String(error)}`));
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [editing, source, viewQuery]);

  useEffect(() => {
    if (editing) editorRef.current?.focus();
    else if (returnEditorFocus.current) {
      returnEditorFocus.current = false;
      editButtonRef.current?.focus();
    }
  }, [editing]);

  useEffect(
    () => () => {
      tokenRequestId.current++;
      wordRequestId.current++;
      kanjiRequestId.current++;
      exampleRequestId.current++;
      translationRequestId.current++;
      saveRequestId.current++;
      sentenceSaveRequestId.current++;
      copyRequestId.current++;
    },
    [],
  );

  useEffect(() => {
    const content = contentRef.current;
    const context = contextRef.current;
    const details = detailsContentRef.current;
    if (!content || !context || !details || !state?.placement) return;
    let frame = 0;
    let lastHeight = 0;
    const updateSize = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        // Measure natural detail content, not the capped scroll viewport.
        const style = getComputedStyle(content);
        const spacing = [
          style.paddingTop,
          style.paddingBottom,
          style.rowGap,
        ].reduce((total, value) => total + (parseFloat(value) || 0), 0);
        const logicalHeight = Math.ceil(
          context.getBoundingClientRect().height +
            details.getBoundingClientRect().height +
            spacing +
            2,
        );
        if (logicalHeight <= 2 || logicalHeight === lastHeight) return;
        lastHeight = logicalHeight;
        void invoke("resize_translation_popup", {
          placement: state.placement,
          logicalHeight,
          viewQuery,
        }).catch((error: unknown) => {
          console.error("YomiMado: could not resize translation popup", error);
        });
      });
    };
    const observer =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(updateSize);
    observer?.observe(context);
    observer?.observe(details);
    updateSize();
    return () => {
      observer?.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [state?.placement, viewQuery]);

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
    const requestId = ++translationRequestId.current;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const nextResult = await requestTranslation(source);
      if (requestId === translationRequestId.current) {
        setResult(nextResult);
        sentenceSaveRequestId.current++;
        setSavingSentence(false);
        setSentenceSaved(false);
      }
    } catch (requestError) {
      if (requestId === translationRequestId.current)
        setError(String(requestError).replace(/^Error: /, ""));
    } finally {
      if (requestId === translationRequestId.current) setLoading(false);
    }
  };

  const saveCurrentSentence = async () => {
    const requestId = ++sentenceSaveRequestId.current;
    setSavingSentence(true);
    setSentenceSaved(false);
    setSentenceSaveError(null);
    try {
      await saveSentence({
        sourceText: source,
        ...(result?.sourceText === source.trim() && {
          translatedText: result.translatedText,
        }),
      });
      if (requestId === sentenceSaveRequestId.current) setSentenceSaved(true);
    } catch (requestError) {
      if (requestId === sentenceSaveRequestId.current)
        setSentenceSaveError(String(requestError).replace(/^Error: /, ""));
    } finally {
      if (requestId === sentenceSaveRequestId.current) setSavingSentence(false);
    }
  };

  const saveWord = async (entry: WordEntry | null, entryIndex: number) => {
    const token = tokens?.[selectedTokenIndex ?? -1];
    if (!token) return;
    const requestId = ++saveRequestId.current;
    setSavingWord(true);
    setSavedEntryIndex(null);
    setSaveError(null);
    try {
      await saveVocabularyWord({
        surface: token.surface,
        reading: entry?.reading ?? token.reading,
        dictionaryForm: token.dictionaryForm,
        meanings: entry?.senses.map((sense) => sense.glosses.join("; ")) ?? [],
        sourceText: source,
      });
      if (requestId === saveRequestId.current) setSavedEntryIndex(entryIndex);
    } catch (requestError) {
      if (requestId === saveRequestId.current)
        setSaveError(String(requestError).replace(/^Error: /, ""));
    } finally {
      if (requestId === saveRequestId.current) setSavingWord(false);
    }
  };

  const analyze = async (text: string = source) => {
    const requestId = ++tokenRequestId.current;
    setTokenLoading(true);
    setTokens(null);
    resetWordSelection();
    setTokenError(null);
    try {
      const nextTokens = await requestTokenization(text);
      if (requestId === tokenRequestId.current) setTokens(nextTokens);
    } catch (requestError) {
      if (requestId === tokenRequestId.current)
        setTokenError(String(requestError).replace(/^Error: /, ""));
    } finally {
      if (requestId === tokenRequestId.current) setTokenLoading(false);
    }
  };

  const applyEdit = () => {
    returnEditorFocus.current = true;
    tokenRequestId.current++;
    setSource(draft);
    translationRequestId.current++;
    setLoading(false);
    setResult(null);
    setError(null);
    sentenceSaveRequestId.current++;
    setSavingSentence(false);
    setSentenceSaved(false);
    setSentenceSaveError(null);
    copyRequestId.current++;
    setCopied(false);
    setCopyError(null);
    setEditing(false);
    void analyze(draft);
  };

  const copySentence = async () => {
    const requestId = ++copyRequestId.current;
    setCopied(false);
    setCopyError(null);
    try {
      await navigator.clipboard.writeText(source);
      if (requestId === copyRequestId.current) setCopied(true);
    } catch {
      if (requestId === copyRequestId.current)
        setCopyError(
          "Could not copy the sentence. Select the text and copy it manually.",
        );
    }
  };

  const selectedToken = tokens?.[selectedTokenIndex ?? -1];
  // Match the native 70% work-area cap; sentence scrolling cannot grow on resize.
  const popupHeightCap = state.placement
    ? Math.max(
        1,
        state.placement.screen.height / state.placement.scaleFactor - 24,
      ) * 0.7
    : 600;
  const sentenceMaxHeight = Math.max(56, Math.min(180, popupHeightCap * 0.3));
  const reviewDescription =
    state.reviewReason || state.approximate
      ? `${state.approximate ? "Approximate OCR region." : "Review OCR."} ${state.reviewReason ?? "Check the text against the page before saving."} Use Edit OCR text to correct it.`
      : null;

  return (
    <div className="translation-popup" aria-label="Japanese learning popup">
      <div className="translation-content" ref={contentRef}>
        <div
          className="popup-context"
          ref={contextRef}
          style={{ maxHeight: popupHeightCap * 0.65 }}
        >
          <div className="translation-heading">
            <div className="translation-heading-labels">
              <span>Japanese</span>
              {reviewDescription && (
                <span
                  className="popup-ocr-status"
                  role="status"
                  title={debugTooltip(reviewDescription)}
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                    aria-hidden="true"
                  >
                    <circle cx="12" cy="12" r="9" />
                    <path d="M12 7v6m0 4v.1" />
                  </svg>
                  <span>Check OCR</span>
                  <span className="visually-hidden"> {reviewDescription}</span>
                </span>
              )}
            </div>
            <button
              className="utility-button utility-icon-button translation-close"
              onClick={(event) => {
                void invoke("close_translation_popup", {
                  returnFocus: event.detail === 0,
                  viewQuery,
                }).catch((error) =>
                  setError(`Could not close popup: ${String(error)}`),
                );
              }}
              aria-label="Close translation"
            >
              ×
            </button>
          </div>
          {state.demo && (
            <p className="popup-metadata">
              Demo boundary — no recognized text. Enter Japanese to try the
              learning tools.
            </p>
          )}
          <div
            className="sentence-scroll"
            style={{ maxHeight: sentenceMaxHeight }}
          >
            <ClickableSentence
              source={source}
              tokens={tokens}
              selectedTokenIndex={selectedTokenIndex}
              onSelect={(index) => {
                detailsRef.current?.scrollTo?.({ top: 0 });
                void selectWord(index);
              }}
            />
          </div>
          <div className="sentence-save-actions">
            <button
              className="utility-button"
              disabled={!source.trim()}
              onClick={() => void copySentence()}
            >
              {copied ? "Copied" : "Copy sentence"}
            </button>
            <button
              className="utility-button"
              disabled={savingSentence || !source.trim()}
              onClick={() => void saveCurrentSentence()}
            >
              {savingSentence ? "Saving…" : "Save sentence"}
            </button>
          </div>
          <div className="sentence-feedback">
            {copied && (
              <p className="popup-success" role="status">
                Sentence copied.
              </p>
            )}
            {copyError && (
              <p className="translation-error" role="alert">
                {copyError}
              </p>
            )}
            {sentenceSaved && (
              <p className="popup-success" role="status">
                Sentence saved locally.
              </p>
            )}
            {sentenceSaveError && (
              <p className="translation-error" role="alert">
                {sentenceSaveError}
              </p>
            )}
          </div>
        </div>
        <div
          className="popup-details"
          ref={detailsRef}
          tabIndex={0}
          aria-label="Learning details"
        >
          <div className="popup-details-content" ref={detailsContentRef}>
            <div className="tokenization-status" role="status">
              {tokenLoading
                ? "Analyzing words…"
                : tokenError
                  ? null
                  : tokens && !tokens.some(isWord)
                    ? "No words found in this text."
                    : "Select a word in the sentence to explore its meaning."}
            </div>
            {tokenError && (
              <div role="alert">
                <p className="translation-error">{tokenError}</p>
                <button
                  className="utility-button analyze-button"
                  disabled={tokenLoading || !source.trim()}
                  onClick={() => void analyze()}
                >
                  Retry word analysis
                </button>
              </div>
            )}
            {selectedToken && (
              <div className="tokenization-selected" key={selectedTokenIndex}>
                <WordDefinition
                  token={selectedToken}
                  entries={wordEntries}
                  loading={wordLoading}
                  error={wordError}
                  saving={savingWord}
                  savedIndex={savedEntryIndex}
                  saveError={saveError}
                  onSave={(entry, index) => void saveWord(entry, index)}
                  onRetry={() => void selectWord(selectedTokenIndex!)}
                />
                <KanjiDetail
                  token={selectedToken}
                  selected={selectedKanji}
                  entry={kanjiEntry}
                  loading={kanjiLoading}
                  error={kanjiError}
                  examples={kanjiExamples}
                  exampleLoading={exampleLoading}
                  exampleError={exampleError}
                  examplesOpen={examplesOpen}
                  onSelect={(character) => void selectKanji(character)}
                  onExpand={(open) => {
                    setExamplesOpen(open);
                    if (open && kanjiExamples === null && !exampleError)
                      void loadExamples();
                  }}
                  onRetryExamples={() => void loadExamples()}
                />
              </div>
            )}
            {editing && (
              <section className="ocr-editor" aria-label="Edit OCR text">
                <label htmlFor="translation-source">
                  {state.demo ? "Demo Japanese text" : "OCR text"}
                </label>
                <textarea
                  ref={editorRef}
                  id="translation-source"
                  lang="ja"
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                />
                <div className="popup-actions">
                  <button
                    className="utility-button utility-button-primary analyze-button"
                    disabled={!draft.trim()}
                    onClick={applyEdit}
                  >
                    Apply and analyze
                  </button>
                  <button className="utility-button" onClick={cancelEdit}>
                    Cancel
                  </button>
                </div>
              </section>
            )}
            <div className="popup-secondary-actions">
              <button
                ref={editButtonRef}
                className="utility-button"
                onClick={() => {
                  setDraft(source);
                  setEditing(true);
                }}
                disabled={editing}
              >
                Edit OCR text
              </button>
              <button
                className="utility-button translate-button"
                onClick={() => void translate()}
                disabled={loading || !source.trim()}
              >
                {loading ? "Translating…" : "Translate locally"}
              </button>
            </div>
            {(error || result || loading) && (
              <section
                className="translation-output"
                aria-label="Requested translation"
                aria-live="polite"
              >
                {loading && <p role="status">Translating locally…</p>}
                {error && (
                  <p className="translation-error" role="alert">
                    {error}
                  </p>
                )}
                {result && (
                  <>
                    <h3>English{result.cached ? " · cached" : ""}</h3>
                    <p lang="en">{result.translatedText}</p>
                  </>
                )}
              </section>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
