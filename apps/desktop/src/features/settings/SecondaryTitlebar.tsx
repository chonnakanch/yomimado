import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";

type WindowAction = "hide" | "minimize" | "toggleMaximize" | "drag";

export function SecondaryTitlebar() {
  const [error, setError] = useState<string | null>(null);
  const control = async (action: WindowAction) => {
    setError(null);
    try {
      await invoke("control_secondary_window", { action });
    } catch (reason) {
      setError(
        `Unable to ${action === "hide" ? "close" : action === "drag" ? "move" : action === "minimize" ? "minimize" : "resize"} this window: ${String(reason)}`,
      );
    }
  };
  return (
    <header className="secondary-titlebar">
      <div className="secondary-titlebar-row">
        <span
          className="secondary-brand secondary-drag-handle"
          title="Drag to move window"
          onMouseDown={(event) => {
            if (event.button === 0) void control("drag");
          }}
        >
          YomiMado <span lang="ja">読み窓</span>
        </span>
        <div
          className="secondary-window-controls"
          role="group"
          aria-label="Window controls"
        >
          <button
            className="utility-button utility-icon-button"
            aria-label="Minimize window"
            title="Minimize window"
            onClick={() => void control("minimize")}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              aria-hidden="true"
            >
              <path d="M5 16h14" />
            </svg>
          </button>
          <button
            className="utility-button utility-icon-button"
            aria-label="Maximize or restore window"
            title="Maximize or restore window"
            onClick={() => void control("toggleMaximize")}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              aria-hidden="true"
            >
              <rect x="5" y="5" width="14" height="14" rx="1" />
            </svg>
          </button>
          <button
            className="utility-button utility-icon-button secondary-close-button"
            aria-label="Close window"
            title="Close window · keep YomiMado running"
            onClick={() => void control("hide")}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              aria-hidden="true"
            >
              <path d="m6 6 12 12M18 6 6 18" />
            </svg>
          </button>
        </div>
      </div>
      {error && (
        <p role="alert" className="secondary-window-error">
          {error}
        </p>
      )}
    </header>
  );
}
