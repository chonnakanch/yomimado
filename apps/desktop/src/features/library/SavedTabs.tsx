import { useRef, type KeyboardEvent } from "react";
import "./library.css";

export type SavedTab = "words" | "sentences";
const tabs: SavedTab[] = ["words", "sentences"];

export function SavedTabs({
  active,
  onChange,
}: {
  active: SavedTab;
  onChange: (tab: SavedTab) => void;
}) {
  const buttons = useRef<Array<HTMLButtonElement | null>>([]);
  const navigate = (event: KeyboardEvent, index: number) => {
    let next: number;
    switch (event.key) {
      case "ArrowRight":
        next = (index + 1) % tabs.length;
        break;
      case "ArrowLeft":
        next = (index + tabs.length - 1) % tabs.length;
        break;
      case "Home":
        next = 0;
        break;
      case "End":
        next = tabs.length - 1;
        break;
      default:
        return;
    }
    event.preventDefault();
    onChange(tabs[next]);
    buttons.current[next]?.focus();
  };
  return (
    <div className="saved-tabs" role="tablist" aria-label="Saved collections">
      {tabs.map((tab, index) => (
        <button
          key={tab}
          ref={(button) => {
            buttons.current[index] = button;
          }}
          className="utility-button"
          id={`saved-tab-${tab}`}
          role="tab"
          aria-selected={active === tab}
          aria-controls={`saved-panel-${tab}`}
          tabIndex={active === tab ? 0 : -1}
          onClick={() => onChange(tab)}
          onKeyDown={(event) => navigate(event, index)}
        >
          {tab === "words" ? "Words" : "Sentences"}
        </button>
      ))}
    </div>
  );
}
