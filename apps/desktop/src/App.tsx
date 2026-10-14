import { useEffect, useState } from "react";
import { SavedTabs, type SavedTab } from "./features/library/SavedTabs";
import { SavedWordsView } from "./features/library/SavedWordsView";
import { SavedSentencesView } from "./features/library/SavedSentencesView";
import { SettingsWindow } from "./features/settings/SettingsWindow";
import { AboutSettings } from "./features/settings/AboutSettings";
import "./features/settings/settings.css";

export function App() {
  const [initialView] = useState(() =>
    new URLSearchParams(window.location.search).get("view"),
  );
  const showSaved = ["saved", "words", "sentences"].includes(initialView ?? "");
  const showSources = initialView === "sources";
  const [savedTab, setSavedTab] = useState<SavedTab>(
    initialView === "sentences" ? "sentences" : "words",
  );
  useEffect(() => {
    if (showSaved) document.getElementById(`saved-tab-${savedTab}`)?.focus();
  }, [showSaved]);
  return (
    <main className="secondary-window">
      <header className="secondary-header">
        <span className="secondary-brand">
          YomiMado <span lang="ja">読み窓</span>
        </span>
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
      {showSources && (
        <section aria-label="Sources and licenses">
          <h1>Sources & licenses</h1>
          <AboutSettings />
        </section>
      )}
      {!showSaved && !showSources && (
        <SettingsWindow
          active
          initialCategory={initialView === "reading" ? "reading" : "scan"}
        />
      )}
      <p className="secondary-footer">
        Closing this window keeps the toolbar running. Quit from More actions on
        the toolbar.
      </p>
    </main>
  );
}
