import { useRef, useState, type KeyboardEvent } from "react";
import { ScanSettings } from "./ScanSettings";
import { ReadingSettings } from "./ReadingSettings";

type Category = "scan" | "reading";
const categories: { id: Category; label: string }[] = [
  { id: "scan", label: "Scan & OCR" },
  { id: "reading", label: "Reading" },
];

export function SettingsWindow({
  active,
  initialCategory,
}: {
  active: boolean;
  initialCategory: Category;
}) {
  const [category, setCategory] = useState(initialCategory);
  const buttons = useRef<Array<HTMLButtonElement | null>>([]);
  const navigate = (event: KeyboardEvent, index: number) => {
    const next =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? categories.length - 1
          : event.key === "ArrowRight"
            ? (index + 1) % categories.length
            : event.key === "ArrowLeft"
              ? (index + categories.length - 1) % categories.length
              : null;
    if (next === null) return;
    event.preventDefault();
    setCategory(categories[next].id);
    buttons.current[next]?.focus();
  };
  return (
    <section hidden={!active} className="settings-window" aria-label="Settings">
      <h1>Settings</h1>
      <p className="secondary-description">
        Set up scanning and your reading controls.
      </p>
      <div
        role="tablist"
        aria-label="Settings categories"
        className="settings-tabs"
      >
        {categories.map(({ id, label }, index) => (
          <button
            key={id}
            ref={(button) => {
              buttons.current[index] = button;
            }}
            className="utility-button"
            role="tab"
            id={`settings-tab-${id}`}
            aria-selected={category === id}
            aria-controls={`settings-panel-${id}`}
            tabIndex={category === id ? 0 : -1}
            onClick={() => setCategory(id)}
            onKeyDown={(event) => navigate(event, index)}
          >
            {label}
          </button>
        ))}
      </div>
      {categories.map(({ id }) => (
        <section
          key={id}
          role="tabpanel"
          id={`settings-panel-${id}`}
          aria-labelledby={`settings-tab-${id}`}
          hidden={category !== id}
        >
          {id === "scan" ? (
            <ScanSettings active={active && category === "scan"} />
          ) : (
            <ReadingSettings />
          )}
        </section>
      ))}
    </section>
  );
}
