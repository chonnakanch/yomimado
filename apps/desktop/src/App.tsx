import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  deleteVocabularyWord,
  listVocabularyWords,
  type SavedWord,
} from "./lib/vocabulary-client";
import {
  readReadingOrderEnabled,
  saveReadingOrderEnabled,
} from "./lib/reading-order-setting";
import {
  deleteSavedSentence,
  listSavedSentences,
  type SavedSentence,
} from "./lib/sentence-client";

interface DetectorModelStatus {
  required: boolean;
  installed: boolean;
}

export function App() {
  const [message, setMessage] = useState("Ready to capture a screen region.");
  const [detectorModel, setDetectorModel] =
    useState<DetectorModelStatus | null>(null);
  const [detectorModelError, setDetectorModelError] = useState<string | null>(
    null,
  );
  const [installingDetectorModel, setInstallingDetectorModel] = useState(false);
  const [showSavedWords, setShowSavedWords] = useState(false);
  const [savedWords, setSavedWords] = useState<SavedWord[]>([]);
  const [savedWordsLoading, setSavedWordsLoading] = useState(false);
  const [savedWordsError, setSavedWordsError] = useState<string | null>(null);
  const [removingWordId, setRemovingWordId] = useState<number | null>(null);
  const [showSavedSentences, setShowSavedSentences] = useState(false);
  const [savedSentences, setSavedSentences] = useState<SavedSentence[]>([]);
  const [sentencesLoading, setSentencesLoading] = useState(false);
  const [sentencesError, setSentencesError] = useState<string | null>(null);
  const [removingSentenceId, setRemovingSentenceId] = useState<number | null>(
    null,
  );
  const [readingOrderEnabled, setReadingOrderEnabled] = useState(
    readReadingOrderEnabled,
  );
  const [showSources, setShowSources] = useState(false);

  useEffect(() => {
    void invoke<DetectorModelStatus>("detector_model_status")
      .then(setDetectorModel)
      .catch((error) => setDetectorModelError(String(error)));
  }, []);

  const installDetectorModel = async () => {
    setInstallingDetectorModel(true);
    setDetectorModelError(null);
    try {
      const updated = await invoke<DetectorModelStatus | null>(
        "install_detector_model",
      );
      if (updated) {
        setDetectorModel(updated);
        setMessage("Detector model installed. You can scan manga now.");
      }
    } catch (error) {
      setDetectorModelError(String(error).replace(/^Error: /, ""));
    } finally {
      setInstallingDetectorModel(false);
    }
  };

  const updateReadingOrder = (enabled: boolean) => {
    try {
      saveReadingOrderEnabled(enabled);
      setReadingOrderEnabled(enabled);
    } catch (error) {
      setMessage(`Unable to save reading-order setting: ${String(error)}`);
    }
  };

  const startCapture = async () => {
    try {
      await invoke("show_capture_selector");
      setMessage("Drag over Japanese text in the capture window.");
    } catch (error) {
      setMessage(`Unable to open capture selection: ${String(error)}`);
    }
  };

  const scanMangaPage = async () => {
    try {
      await invoke("show_auto_scanner");
      setMessage("Finding the manga page; saved area is the fallback.");
    } catch (error) {
      setMessage(`Unable to scan the manga page: ${String(error)}`);
    }
  };

  const adjustScanArea = async () => {
    try {
      await invoke("show_scan_area_selector");
      setMessage("Drag around the manga reading area to save and scan it.");
    } catch (error) {
      setMessage(`Unable to set the scan area: ${String(error)}`);
    }
  };

  const loadSavedWords = async () => {
    setShowSavedWords(true);
    setSavedWordsLoading(true);
    setSavedWordsError(null);
    try {
      setSavedWords(await listVocabularyWords());
    } catch (error) {
      setSavedWordsError(String(error).replace(/^Error: /, ""));
    } finally {
      setSavedWordsLoading(false);
    }
  };

  const removeWord = async (word: SavedWord) => {
    if (!window.confirm(`Remove ${word.surface} from saved words?`)) return;
    setRemovingWordId(word.id);
    setSavedWordsError(null);
    try {
      await deleteVocabularyWord(word.id);
      setSavedWords((previous) =>
        previous.filter((item) => item.id !== word.id),
      );
    } catch (error) {
      setSavedWordsError(String(error).replace(/^Error: /, ""));
    } finally {
      setRemovingWordId(null);
    }
  };

  const loadSavedSentences = async () => {
    setShowSavedSentences(true);
    setSentencesLoading(true);
    setSentencesError(null);
    try {
      setSavedSentences(await listSavedSentences());
    } catch (error) {
      setSentencesError(String(error).replace(/^Error: /, ""));
    } finally {
      setSentencesLoading(false);
    }
  };

  const removeSentence = async (sentence: SavedSentence) => {
    if (!window.confirm("Remove this saved sentence?")) return;
    setRemovingSentenceId(sentence.id);
    setSentencesError(null);
    try {
      await deleteSavedSentence(sentence.id);
      setSavedSentences((previous) =>
        previous.filter((item) => item.id !== sentence.id),
      );
    } catch (error) {
      setSentencesError(String(error).replace(/^Error: /, ""));
    } finally {
      setRemovingSentenceId(null);
    }
  };

  return (
    <main className="main-window">
      <h1>
        YomiMado <span>読み窓</span>
      </h1>
      <p>Read beyond the page.</p>
      {detectorModel?.required && (
        <section className="model-setup" aria-label="Detector model setup">
          <h2>Detector model</h2>
          {detectorModel.installed ? (
            <p>Installed on this computer. Manga scanning is ready.</p>
          ) : (
            <p>
              Download <code>comictextdetector.pt.onnx</code> from the{" "}
              <a
                href="https://github.com/zyddnys/manga-image-translator/releases/tag/beta-0.2.1"
                target="_blank"
                rel="noreferrer"
              >
                original release page
              </a>
              , then select the downloaded file. YomiMado checks it and stores a
              private copy in its app data. Nothing is downloaded by the app.
            </p>
          )}
          <button
            className="secondary-button"
            onClick={() => void installDetectorModel()}
            disabled={installingDetectorModel}
          >
            {installingDetectorModel
              ? "Checking model…"
              : detectorModel.installed
                ? "Replace detector model"
                : "Select detector model file"}
          </button>
          {detectorModelError && (
            <p className="translation-error" role="alert">
              {detectorModelError}
            </p>
          )}
        </section>
      )}
      {detectorModelError && !detectorModel?.required && (
        <p className="translation-error" role="alert">
          Unable to check detector model setup: {detectorModelError}
        </p>
      )}
      <div className="main-actions">
        <button
          onClick={startCapture}
          disabled={detectorModel?.required && !detectorModel.installed}
        >
          Select screen region
        </button>
        <button
          onClick={scanMangaPage}
          disabled={detectorModel?.required && !detectorModel.installed}
        >
          Scan manga page
        </button>
        <button
          className="secondary-button"
          onClick={adjustScanArea}
          disabled={detectorModel?.required && !detectorModel.installed}
        >
          Set/adjust scan area
        </button>
        <button
          className="secondary-button"
          onClick={() =>
            showSavedWords ? setShowSavedWords(false) : void loadSavedWords()
          }
        >
          {showSavedWords ? "Hide saved words" : "Saved words"}
        </button>
        <button
          className="secondary-button"
          onClick={() =>
            showSavedSentences
              ? setShowSavedSentences(false)
              : void loadSavedSentences()
          }
        >
          {showSavedSentences ? "Hide saved sentences" : "Saved sentences"}
        </button>
      </div>
      <p className="status">{message}</p>
      <p className="hint">
        Shortcuts: Cmd/Ctrl + Shift + O for manual selection; Cmd/Ctrl + Shift +
        S to scan the manga page.
      </p>
      <section className="main-settings" aria-label="Reading settings">
        <h2>Reading settings</h2>
        <label className="setting-option">
          <input
            type="checkbox"
            checked={readingOrderEnabled}
            onChange={(event) =>
              updateReadingOrder(event.currentTarget.checked)
            }
          />
          <span>
            <strong>Reading-order controls</strong>
            <small>Show navigation on page scans. Off by default.</small>
          </span>
        </label>
      </section>
      <section className="main-settings" aria-label="Sources and licenses">
        <button
          className="secondary-button sources-toggle"
          aria-expanded={showSources}
          onClick={() => setShowSources((previous) => !previous)}
        >
          {showSources ? "Hide sources and licenses" : "Sources and licenses"}
        </button>
        {showSources && (
          <div className="sources-content">
            <p>
              Word and kanji data: JMdict and KANJIDIC2, copyright James William
              Breen and the Electronic Dictionary Research and Development Group
              (EDRDG), licensed under CC BY-SA 4.0. See the{" "}
              <a
                href="https://www.edrdg.org/edrdg/licence.html"
                target="_blank"
                rel="noreferrer"
              >
                dictionary licence and source
              </a>
              .
            </p>
            <p>
              OCR recognition: Manga OCR by kha-white. Translation: Helsinki-NLP
              opus-mt-ja-en. Both models are identified as Apache-2.0 by their{" "}
              <a
                href="https://huggingface.co/kha-white/manga-ocr-base"
                target="_blank"
                rel="noreferrer"
              >
                Manga OCR
              </a>{" "}
              and{" "}
              <a
                href="https://huggingface.co/Helsinki-NLP/opus-mt-ja-en"
                target="_blank"
                rel="noreferrer"
              >
                translation model
              </a>{" "}
              cards. Text detection code is from{" "}
              <a
                href="https://github.com/dmMaze/comic-text-detector"
                target="_blank"
                rel="noreferrer"
              >
                comic-text-detector
              </a>
              ; detector weights are installed separately by you.
            </p>
            <p>
              The packaged app also includes full model, dictionary, and
              software notices in its <code>ocr/notices</code> folder (inside
              Resources on macOS).
            </p>
          </div>
        )}
      </section>
      {showSavedWords && (
        <section className="saved-words" aria-label="Saved words">
          <div className="saved-words-heading">
            <h2>Saved words</h2>
            <button
              className="secondary-button"
              onClick={() => void loadSavedWords()}
              disabled={savedWordsLoading}
            >
              Refresh
            </button>
          </div>
          {savedWordsLoading && <p>Loading saved words…</p>}
          {savedWordsError && (
            <p className="translation-error" role="alert">
              {savedWordsError}
            </p>
          )}
          {!savedWordsLoading &&
            !savedWordsError &&
            savedWords.length === 0 && (
              <p>
                No saved words yet. Choose a word in the learning popup to save
                it.
              </p>
            )}
          <ul className="saved-word-list">
            {savedWords.map((word) => (
              <li key={word.id}>
                <div className="saved-word-top">
                  <div>
                    <strong lang="ja">{word.surface}</strong>{" "}
                    <span lang="ja">{word.reading}</span>
                    {word.dictionaryForm !== word.surface && (
                      <small>Base: {word.dictionaryForm}</small>
                    )}
                  </div>
                  <button
                    className="secondary-button"
                    disabled={removingWordId === word.id}
                    onClick={() => void removeWord(word)}
                    aria-label={`Remove ${word.surface}`}
                  >
                    {removingWordId === word.id ? "Removing…" : "Remove"}
                  </button>
                </div>
                {word.meanings.length > 0 ? (
                  <ol>
                    {word.meanings.map((meaning, index) => (
                      <li key={index}>{meaning}</li>
                    ))}
                  </ol>
                ) : (
                  <p className="hint">No dictionary meaning saved.</p>
                )}
                <p lang="ja" className="saved-word-context">
                  {word.sourceText}
                </p>
                <small>Saved {new Date(word.createdAt).toLocaleString()}</small>
                {word.meanings.length > 0 && (
                  <small>
                    Possible dictionary senses · Source:{" "}
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
              </li>
            ))}
          </ul>
        </section>
      )}
      {showSavedSentences && (
        <section className="saved-words" aria-label="Saved sentences">
          <div className="saved-words-heading">
            <h2>Saved sentences</h2>
            <button
              className="secondary-button"
              onClick={() => void loadSavedSentences()}
              disabled={sentencesLoading}
            >
              Refresh
            </button>
          </div>
          {sentencesLoading && <p>Loading saved sentences…</p>}
          {sentencesError && (
            <p className="translation-error" role="alert">
              {sentencesError}
            </p>
          )}
          {!sentencesLoading &&
            !sentencesError &&
            savedSentences.length === 0 && (
              <p>No saved sentences yet. Save one in the learning popup.</p>
            )}
          <ul className="saved-word-list">
            {savedSentences.map((sentence) => (
              <li key={sentence.id}>
                <div className="saved-word-top">
                  <strong lang="ja">{sentence.sourceText}</strong>
                  <button
                    className="secondary-button"
                    disabled={removingSentenceId === sentence.id}
                    onClick={() => void removeSentence(sentence)}
                    aria-label={`Remove saved sentence ${sentence.id}`}
                  >
                    {removingSentenceId === sentence.id
                      ? "Removing…"
                      : "Remove"}
                  </button>
                </div>
                {sentence.translatedText && <p>{sentence.translatedText}</p>}
                <small>
                  Saved {new Date(sentence.createdAt).toLocaleString()}
                </small>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
