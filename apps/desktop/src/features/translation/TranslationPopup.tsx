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
import { ManualWordSelection } from "./ManualWordSelection";
import { WordDefinition } from "./WordDefinition";
import { KanjiDetail } from "./KanjiDetail";
import { PopupIcon } from "./PopupIcon";
import { PopupModes, type PopupMode } from "./PopupModes";
import { TranslationOutput } from "./TranslationOutput";
import { explainConjugation, type ConjugationAnalysis } from "./conjugation";
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
  const wordsButtonRef = useRef<HTMLButtonElement>(null);
  const returnEditorFocus = useRef(false);
  const [selectingText, setSelectingText] = useState(false);
  const [editing, setEditing] = useState(state?.demo ?? false);
  const [draft, setDraft] = useState(state?.demo ? "" : (state?.text ?? ""));
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);
  const copyRequestId = useRef(0);
  const viewQuery = useRef(window.location.search.slice(1)).current;
  const [source, setSource] = useState(state?.demo ? "" : (state?.text ?? ""));
  const [result, setResult] = useState<TranslationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [popupError, setPopupError] = useState<string | null>(null);
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
  const [selectedToken, setSelectedToken] = useState<TextToken | null>(null);
  const [conjugation, setConjugation] = useState<ConjugationAnalysis | null>(
    null,
  );
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
    setSelectedToken(null);
    setConjugation(null);
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

  const lookupWord = async (token: TextToken, tokenIndex: number | null) => {
    const requestId = ++wordRequestId.current;
    const explanation = explainConjugation(
      source,
      tokens ?? [],
      token,
      tokenIndex === null,
    );
    setConjugation(explanation);
    // An exact, supported manual expression can reuse the tokenizer's base form.
    // The selected source text and its offsets remain unchanged.
    if (tokenIndex === null && explanation?.status === "supported") {
      token = { ...token, dictionaryForm: explanation.dictionaryForm };
    }
    kanjiRequestId.current++;
    setSelectedTokenIndex(tokenIndex);
    setSelectedToken(token);
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

  const selectWord = (tokenIndex: number) => {
    const token = tokens?.[tokenIndex];
    if (!token) return;
    if (
      tokenIndex === selectedTokenIndex &&
      (wordLoading || wordEntries !== null)
    )
      return;
    void lookupWord(token, tokenIndex);
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
    const token = selectedToken;
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
      // Escape can cancel Japanese IME candidates without cancelling the draft.
      if (event.key !== "Escape" || event.isComposing || event.keyCode === 229)
        return;
      event.preventDefault();
      if (editing) {
        cancelEdit();
        return;
      }
      if (selectingText) {
        setSelectingText(false);
        wordsButtonRef.current?.focus();
        return;
      }
      void invoke("close_translation_popup", {
        returnFocus: true,
        viewQuery,
      }).catch((error) =>
        setPopupError(`Could not close popup: ${String(error)}`),
      );
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [editing, selectingText, source, viewQuery]);

  useEffect(() => {
    if (editing) editorRef.current?.focus();
    else if (returnEditorFocus.current) {
      returnEditorFocus.current = false;
      wordsButtonRef.current?.focus();
    }
  }, [editing]);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 1500);
    return () => clearTimeout(timer);
  }, [copied]);

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

  const mode: PopupMode = editing ? "edit" : selectingText ? "select" : "words";
  const changeMode = (next: PopupMode) => {
    if (next === mode) return;
    returnEditorFocus.current = false;
    setDraft(source);
    setSelectingText(next === "select");
    setEditing(next === "edit");
  };

  const translate = async () => {
    if (loading || editing || !source.trim()) return;
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
    if (savingSentence || sentenceSaved || editing || !source.trim()) return;
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
    const token = selectedToken;
    if (!token) return;
    const requestId = ++saveRequestId.current;
    setSavingWord(true);
    setSavedEntryIndex(null);
    setSaveError(null);
    try {
      await saveVocabularyWord({
        surface: token.surface,
        reading: entry?.reading ?? token.reading,
        dictionaryForm: entry?.expression ?? token.dictionaryForm,
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
      ? `${state.approximate ? "Approximate OCR region." : "Review OCR."} ${state.reviewReason ?? "Check the text against the page before saving."} Use Edit to correct it.`
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
              type="button"
              className="utility-button utility-icon-button translation-close"
              onClick={(event) => {
                void invoke("close_translation_popup", {
                  returnFocus: event.detail === 0,
                  viewQuery,
                }).catch((error) =>
                  setPopupError(`Could not close popup: ${String(error)}`),
                );
              }}
              aria-label="Close translation"
            >
              <PopupIcon name="close" />
            </button>
          </div>
          {state.demo && (
            <p className="popup-metadata">
              Demo boundary — no recognized text. Enter Japanese to try the
              learning tools.
            </p>
          )}
          <PopupModes
            mode={mode}
            onChange={changeMode}
            canSelect={!!source.trim()}
            wordsRef={wordsButtonRef}
          />
          <section
            className="sentence-card"
            hidden={editing}
            aria-label="Japanese sentence and actions"
          >
            <div
              role="tabpanel"
              id="popup-panel-words"
              aria-labelledby="popup-mode-words"
              hidden={mode !== "words"}
            >
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
                    selectWord(index);
                  }}
                />
              </div>
            </div>
            <div
              role="tabpanel"
              id="popup-panel-select"
              aria-labelledby="popup-mode-select"
              hidden={mode !== "select"}
            >
              {selectingText && (
                <ManualWordSelection
                  source={source}
                  maxHeight={sentenceMaxHeight}
                  onLookup={(token) => {
                    detailsRef.current?.scrollTo?.({ top: 0 });
                    void lookupWord(token, null);
                  }}
                />
              )}
            </div>
            <div
              className="sentence-save-actions"
              aria-label="Sentence actions"
            >
              <button
                type="button"
                className={`utility-button popup-action${copied ? " is-copied" : ""}`}
                aria-label={copied ? "Copied" : "Copy sentence"}
                disabled={editing || !source.trim()}
                onClick={() => void copySentence()}
              >
                <PopupIcon name={copied ? "check" : "copy"} />
                <span>{copied ? "Copied" : "Copy"}</span>
              </button>
              <button
                type="button"
                className={`utility-button popup-action${sentenceSaved ? " is-saved" : ""}`}
                aria-label={
                  sentenceSaved ? "Sentence saved locally" : "Save sentence"
                }
                aria-busy={savingSentence}
                disabled={
                  editing || savingSentence || sentenceSaved || !source.trim()
                }
                onClick={() => void saveCurrentSentence()}
              >
                <PopupIcon name={savingSentence ? "loading" : "bookmark"} />
                <span>
                  {savingSentence
                    ? "Saving…"
                    : sentenceSaved
                      ? "Saved"
                      : "Save"}
                </span>
              </button>
              <button
                type="button"
                className={`utility-button popup-action translate-button${loading || result ? " is-active" : ""}${error ? " is-error" : ""}`}
                aria-label={
                  error
                    ? "Retry translation"
                    : loading
                      ? "Translating locally"
                      : "Translate locally"
                }
                aria-busy={loading}
                disabled={editing || loading || !source.trim()}
                onClick={() => void translate()}
              >
                <PopupIcon
                  name={loading ? "loading" : error ? "retry" : "translate"}
                />
                <span>
                  {loading ? "Translating…" : error ? "Retry" : "Translate"}
                </span>
              </button>
            </div>
            <div className="sentence-feedback">
              <span className="visually-hidden" role="status">
                {copied ? "Sentence copied." : ""}{" "}
                {sentenceSaved ? "Sentence saved locally." : ""}
              </span>
              {copyError && (
                <p className="translation-error" role="alert">
                  {copyError}
                </p>
              )}
              {sentenceSaveError && (
                <p className="translation-error" role="alert">
                  {sentenceSaveError}
                </p>
              )}
            </div>
          </section>
          <section
            className="ocr-editor"
            role="tabpanel"
            id="popup-panel-edit"
            aria-labelledby="popup-mode-edit"
            hidden={!editing}
          >
            {editing && (
              <>
                <p className="popup-metadata">
                  Fix any characters OCR got wrong. Apply splits the sentence
                  into words again.
                </p>
                <label className="visually-hidden" htmlFor="translation-source">
                  {state.demo ? "Demo Japanese text" : "OCR text"}
                </label>
                <textarea
                  ref={editorRef}
                  id="translation-source"
                  lang="ja"
                  spellCheck={false}
                  value={draft}
                  rows={3}
                  onChange={(event) => setDraft(event.target.value)}
                />
                <div className="popup-actions editor-actions">
                  <button
                    type="button"
                    className="inline-action editor-reset"
                    onClick={() => {
                      setDraft(state.demo ? "" : state.text);
                      editorRef.current?.focus();
                    }}
                  >
                    Reset to OCR text
                  </button>
                  <button
                    type="button"
                    className="utility-button"
                    onClick={cancelEdit}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="utility-button utility-button-primary analyze-button"
                    disabled={!draft.trim()}
                    onClick={applyEdit}
                  >
                    Apply
                  </button>
                </div>
              </>
            )}
          </section>
          {popupError && (
            <p className="translation-error" role="alert">
              {popupError}
            </p>
          )}
        </div>
        <div
          className="popup-details"
          ref={detailsRef}
          tabIndex={0}
          aria-label="Learning details"
          hidden={editing}
        >
          <div className="popup-details-content" ref={detailsContentRef}>
            {(error || result || loading) && (
              <TranslationOutput
                key={`${result?.provider ?? "pending"}:${result?.sourceText ?? source}:${result?.translatedText ?? ""}`}
                result={result}
                loading={loading}
                error={error}
                saved={sentenceSaved && result?.sourceText === source.trim()}
              />
            )}
            <div className="tokenization-status" role="status">
              {tokenLoading
                ? "Analyzing words…"
                : tokenError || selectedToken
                  ? null
                  : selectingText
                    ? "Select text and choose Look up selection to explore its meaning."
                    : tokens && !tokens.some(isWord)
                      ? "No words found in this text."
                      : "Tap a word to see its meaning."}
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
              <div
                className="tokenization-selected"
                key={`${selectedToken.start}-${selectedToken.end}-${selectedTokenIndex}`}
              >
                <WordDefinition
                  token={selectedToken}
                  manualSelection={selectedTokenIndex === null}
                  conjugation={conjugation}
                  entries={wordEntries}
                  loading={wordLoading}
                  error={wordError}
                  saving={savingWord}
                  savedIndex={savedEntryIndex}
                  saveError={saveError}
                  onSave={(entry, index) => void saveWord(entry, index)}
                  onRetry={() =>
                    void lookupWord(selectedToken, selectedTokenIndex)
                  }
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
          </div>
        </div>
      </div>
    </div>
  );
}
