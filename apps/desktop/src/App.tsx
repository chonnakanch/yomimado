import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  readReadingOrderEnabled,
  saveReadingOrderEnabled,
} from "./lib/reading-order-setting";
import { SavedTabs, type SavedTab } from "./features/library/SavedTabs";
import { SavedWordsView } from "./features/library/SavedWordsView";
import { SavedSentencesView } from "./features/library/SavedSentencesView";

interface DetectorModelStatus {
  required: boolean;
  installed: boolean;
}

export function App() {
  const [initialView] = useState(() =>
    new URLSearchParams(window.location.search).get("view"),
  );
  const libraryOnly = ["saved", "words", "sentences"].includes(
    initialView ?? "",
  );
  const [showSaved, setShowSaved] = useState(libraryOnly);
  const [savedTab, setSavedTab] = useState<SavedTab>(
    initialView === "sentences" ? "sentences" : "words",
  );
  const [message, setMessage] = useState("Ready to capture a screen region.");
  const [detectorModel, setDetectorModel] =
    useState<DetectorModelStatus | null>(null);
  const [detectorModelError, setDetectorModelError] = useState<string | null>(
    null,
  );
  const [installingDetectorModel, setInstallingDetectorModel] = useState(false);
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

  useEffect(() => {
    const view = new URLSearchParams(window.location.search).get("view");
    if (view === "sources") setShowSources(true);
    if (view === "settings") {
      document.getElementById("scan-ocr-settings")?.scrollIntoView?.();
    }
  }, []);

  useEffect(() => {
    if (showSaved) document.getElementById(`saved-tab-${savedTab}`)?.focus();
  }, [showSaved]);

  return (
    <main className={`main-window${libraryOnly ? " saved-library-view" : ""}`}>
      {libraryOnly ? (
        <>
          <h1>Saved</h1>
          <p>Words and sentences kept locally.</p>
        </>
      ) : (
        <>
          <h1>
            YomiMado <span>読み窓</span>
          </h1>
          <p>Read beyond the page.</p>
          {detectorModel?.required && (
            <section
              className="model-setup"
              aria-label="Detector model setup"
              id="scan-ocr-settings"
            >
              <h2>Scan & OCR · Detector model</h2>
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
                  , then select the downloaded file. YomiMado checks it and
                  stores a private copy in its app data. Nothing is downloaded
                  by the app.
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
              aria-expanded={showSaved}
              aria-controls="saved-library"
              onClick={() => setShowSaved((previous) => !previous)}
            >
              {showSaved ? "Hide saved" : "Saved"}
            </button>
          </div>
          <p className="status">{message}</p>
          <p className="hint">
            Shortcuts: Cmd/Ctrl + Shift + O for manual selection; Cmd/Ctrl +
            Shift + S for Whole Screen. The toolbar is the primary reading
            control; closing this window keeps YomiMado running.
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
              {showSources
                ? "Hide sources and licenses"
                : "Sources and licenses"}
            </button>
            {showSources && (
              <div className="sources-content">
                <p>
                  Word and kanji data: JMdict and KANJIDIC2, copyright James
                  William Breen and the Electronic Dictionary Research and
                  Development Group (EDRDG), licensed under CC BY-SA 4.0. See
                  the{" "}
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
                  OCR recognition: Manga OCR by kha-white. Translation:
                  Helsinki-NLP opus-mt-ja-en. Both models are identified as
                  Apache-2.0 by their{" "}
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
                  software notices in its <code>ocr/notices</code> folder
                  (inside Resources on macOS).
                </p>
              </div>
            )}
          </section>
        </>
      )}
      {showSaved && (
        <section
          className="saved-library"
          aria-label="Saved"
          id="saved-library"
        >
          {!libraryOnly && <h2>Saved</h2>}
          <SavedTabs active={savedTab} onChange={setSavedTab} />
          <SavedWordsView active={savedTab === "words"} />
          <SavedSentencesView active={savedTab === "sentences"} />
        </section>
      )}
    </main>
  );
}
