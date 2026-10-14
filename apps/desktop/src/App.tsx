import { useEffect, useState } from "react";
import { SavedTabs, type SavedTab } from "./features/library/SavedTabs";
import { SavedWordsView } from "./features/library/SavedWordsView";
import { SavedSentencesView } from "./features/library/SavedSentencesView";
import { SettingsWindow } from "./features/settings/SettingsWindow";
import { SecondaryTitlebar } from "./features/settings/SecondaryTitlebar";
import "./features/settings/settings.css";

export function App() {
  const [initialView] = useState(() =>
    new URLSearchParams(window.location.search).get("view"),
  );
  const [showSaved, setShowSaved] = useState(
    ["saved", "words", "sentences"].includes(initialView ?? ""),
  );
  const [savedTab, setSavedTab] = useState<SavedTab>(
    initialView === "sentences" ? "sentences" : "words",
  );
  useEffect(() => {
    if (showSaved) document.getElementById(`saved-tab-${savedTab}`)?.focus();
  }, [showSaved]);
  return (
    <div className="secondary-shell">
      <SecondaryTitlebar />
      <main className="secondary-window">
        <header className="secondary-header">
          <nav aria-label="Library and settings">
            <button
              className="utility-button"
              aria-current={showSaved ? "page" : undefined}
              onClick={() => setShowSaved(true)}
            >
              Saved
            </button>
            <button
              className="utility-button"
              aria-current={!showSaved ? "page" : undefined}
              onClick={() => setShowSaved(false)}
            >
              Settings
            </button>
          </nav>
        </header>
        {showSaved && (
          <section
            className="saved-library"
            aria-label="Saved"
            id="saved-library"
          >
            <h1>Saved</h1>
            <p className="secondary-description">
              Words and sentences kept locally.
            </p>
            <SavedTabs active={savedTab} onChange={setSavedTab} />
            <SavedWordsView active={savedTab === "words"} />
            <SavedSentencesView active={savedTab === "sentences"} />
          </section>
        )}
        <SettingsWindow
          active={!showSaved}
          initialCategory={
            initialView === "sources"
              ? "about"
              : initialView === "reading"
                ? "reading"
                : "scan"
          }
        />
        <p className="secondary-footer">
          Close window keeps the toolbar running. Quit from More actions on the
          toolbar.
        </p>
      </main>
    </div>
  );
}
