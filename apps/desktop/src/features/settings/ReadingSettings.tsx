import { useState } from "react";
import {
  readReadingOrderEnabled,
  saveReadingOrderEnabled,
} from "../../lib/reading-order-setting";

export function ReadingSettings() {
  const [enabled, setEnabled] = useState(readReadingOrderEnabled);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const update = (next: boolean) => {
    try {
      saveReadingOrderEnabled(next);
      setEnabled(next);
      setError(null);
      setMessage("Reading preference saved. Applies to new scans.");
    } catch (reason) {
      setMessage("");
      setError(`Unable to save reading-order setting: ${String(reason)}`);
    }
  };
  return (
    <div className="settings-card">
      <h2>Reading</h2>
      <label className="settings-option">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(event) => update(event.currentTarget.checked)}
          aria-describedby="reading-order-help"
        />
        <span>Reading-order controls</span>
      </label>
      <p id="reading-order-help">
        Show estimated Previous/Next navigation on new scans. Off by default.
        The order uses text positions and may differ from manga panel order; you
        can still click any region.
      </p>
      <p className="settings-note">
        Keyboard region navigation through More actions → Focus regions is
        always available with OCR results.
      </p>
      {error && (
        <p role="alert" className="settings-error">
          {error}
        </p>
      )}
      <p role="status" className="settings-success">
        {message}
      </p>
    </div>
  );
}
