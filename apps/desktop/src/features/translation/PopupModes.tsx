import type { KeyboardEvent, RefObject } from "react";
import { PopupIcon } from "./PopupIcon";

export type PopupMode = "words" | "select" | "edit";
const modes = ["words", "select", "edit"] as const;
const labels = { words: "Words", select: "Select", edit: "Edit" };

export function PopupModes({
  mode,
  onChange,
  canSelect,
  wordsRef,
}: {
  mode: PopupMode;
  onChange: (mode: PopupMode) => void;
  canSelect: boolean;
  wordsRef: RefObject<HTMLButtonElement | null>;
}) {
  const navigate = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const buttons = Array.from(
      event.currentTarget.parentElement!.querySelectorAll<HTMLButtonElement>(
        "button:not(:disabled)",
      ),
    );
    const index = buttons.indexOf(event.currentTarget);
    const next =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? buttons.length - 1
          : (index + (event.key === "ArrowRight" ? 1 : -1) + buttons.length) %
            buttons.length;
    buttons[next]?.focus();
  };
  return (
    <div className="popup-modes" role="tablist" aria-label="Japanese text mode">
      {modes.map((item) => (
        <button
          type="button"
          className="utility-button"
          role="tab"
          key={item}
          id={`popup-mode-${item}`}
          aria-selected={mode === item}
          aria-controls={`popup-panel-${item}`}
          tabIndex={mode === item ? 0 : -1}
          disabled={item === "select" && !canSelect}
          ref={item === "words" ? wordsRef : undefined}
          onClick={() => onChange(item)}
          onKeyDown={navigate}
        >
          <PopupIcon name={item} />
          {labels[item]}
        </button>
      ))}
    </div>
  );
}
