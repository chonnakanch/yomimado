import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  deleteVocabularyWord,
  listVocabularyWords,
  type SavedWord,
} from "./lib/vocabulary-client";

export function App() {
  const [message, setMessage] = useState("Ready to capture a screen region.");
  const [showSavedWords, setShowSavedWords] = useState(false);
  const [savedWords, setSavedWords] = useState<SavedWord[]>([]);
  const [savedWordsLoading, setSavedWordsLoading] = useState(false);
  const [savedWordsError, setSavedWordsError] = useState<string | null>(null);
  const [removingWordId, setRemovingWordId] = useState<number | null>(null);

  const startCapture = async () => {
    try {
      await invoke("show_capture_selector");
      setMessage("Drag over Japanese text in the capture window.");
    } catch (error) {
      setMessage(`Unable to open capture selection: ${String(error)}`);
    }
  };

  const scanSavedArea = async () => {
    try {
      await invoke("show_saved_area_scanner");
      setMessage("Scanning the saved manga area on this display.");
    } catch (error) {
      setMessage(`Unable to scan the manga area: ${String(error)}`);
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

  return (
    <main className="main-window">
      <h1>
        YomiMado <span>読み窓</span>
      </h1>
      <p>Read beyond the page.</p>
      <div className="main-actions">
        <button onClick={startCapture}>Select screen region</button>
        <button onClick={scanSavedArea}>Scan manga area</button>
        <button className="secondary-button" onClick={adjustScanArea}>
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
      </div>
      <p className="status">{message}</p>
      <p className="hint">Shortcut: Cmd/Ctrl + Shift + O</p>
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
    </main>
  );
}
