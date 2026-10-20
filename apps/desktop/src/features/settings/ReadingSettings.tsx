import { TranslationModels } from "./TranslationModels";
import { useState } from "react";
import { setJlptVisible, useJlptVisible } from "../jlpt/preference";
import { jlptSource } from "../jlpt/jlpt";

export function ReadingSettings({ active = false }: { active?: boolean }) {
  const showJlpt = useJlptVisible();
  const [jlptError, setJlptError] = useState<string | null>(null);
  return (
    <>
      <TranslationModels active={active} />
      <div className="settings-card">
        <h2>JLPT vocabulary</h2>
        <label className="settings-option">
          <input
            type="checkbox"
            checked={showJlpt}
            onChange={(event) => {
              try {
                setJlptVisible(event.currentTarget.checked);
                setJlptError(null);
              } catch {
                setJlptError(
                  "Could not save the JLPT display preference. Try again.",
                );
              }
            }}
          />
          Show estimated JLPT levels (N5–N1)
        </label>
        <p className="settings-note">
          Community estimates, not official exam assignments. Unlisted words
          stay unclassified. Tags work offline in word definitions and Saved.
          Source:{" "}
          <a href={jlptSource} target="_blank" rel="noreferrer">
            Jonathan Waller / Stephen Kraus
          </a>{" "}
          · CC BY-SA 4.0.
        </p>
        {jlptError && (
          <p className="settings-error" role="alert">
            {jlptError}
          </p>
        )}
      </div>
      <div className="settings-card">
        <h2>Reading</h2>
        <h3>Read with keyboard</h3>
        <p>
          After scanning, choose More actions → Read with keyboard on the
          toolbar. Show the OCR overlays first if they are hidden.
        </p>
        <p>
          Arrow keys move between regions. Home and End select the first and
          last region. Enter or Space opens the selected region’s learning
          popup. Escape closes the popup and returns to that region; press
          Escape again to hide the overlays and return to the toolbar.
        </p>
        <p className="settings-note">
          Navigation follows detected regions. Estimated order on whole-screen
          scans may differ from manga panel order; you can still click any
          region.
        </p>
      </div>
    </>
  );
}
