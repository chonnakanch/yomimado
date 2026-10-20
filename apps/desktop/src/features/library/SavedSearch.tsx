import { useRef, useState } from "react";
import type { SavedTab } from "./SavedTabs";

const queryKey = (kind: SavedTab) => `yomimado.saved-search.${kind}.v1`;

export function useSavedQuery(kind: SavedTab) {
  const [query, setQuery] = useState(() => {
    try {
      return (window.localStorage.getItem(queryKey(kind)) ?? "").slice(0, 200);
    } catch {
      return "";
    }
  });
  const update = (value: string) => {
    const next = value.slice(0, 200);
    setQuery(next);
    try {
      if (next) window.localStorage.setItem(queryKey(kind), next);
      else window.localStorage.removeItem(queryKey(kind));
    } catch {
      // Search remains usable if local storage is unavailable.
    }
  };
  return [query, update] as const;
}

export function SavedSearch({
  kind,
  query,
  onChange,
}: {
  kind: SavedTab;
  query: string;
  onChange: (query: string) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <div className="library-search">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        aria-hidden="true"
      >
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="m16 16 4.5 4.5" />
      </svg>
      <input
        id={`saved-search-${kind}`}
        ref={input}
        type="search"
        aria-label={`Search saved ${kind}`}
        aria-controls={`saved-${kind}-results`}
        placeholder={
          kind === "words"
            ? "Japanese, reading, or meaning…"
            : "Japanese or saved translation…"
        }
        value={query}
        maxLength={200}
        autoComplete="off"
        spellCheck={false}
        onChange={(event) => onChange(event.currentTarget.value)}
        onKeyDown={(event) => {
          // Do not consume Escape while an IME is composing Japanese.
          if (
            event.key === "Escape" &&
            !event.nativeEvent.isComposing &&
            query
          ) {
            event.preventDefault();
            onChange("");
          }
        }}
      />
      {query && (
        <button
          className="library-search-clear"
          aria-label={`Clear ${kind} search`}
          onClick={() => {
            onChange("");
            input.current?.focus();
          }}
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            aria-hidden="true"
          >
            <path d="m7 7 10 10M17 7 7 17" />
          </svg>
        </button>
      )}
    </div>
  );
}

export function NoSearchResults({
  kind,
  onClear,
}: {
  kind: SavedTab;
  onClear: () => void;
}) {
  return (
    <div className="library-empty library-no-results">
      <h3>No matching {kind}</h3>
      <p>
        {kind === "words"
          ? "Try a word, reading, meaning, or phrase from its source sentence."
          : "Try Japanese text or a phrase from a saved translation."}
      </p>
      <button
        className="utility-button"
        onClick={() => {
          onClear();
          document.getElementById(`saved-search-${kind}`)?.focus();
        }}
      >
        Clear search
      </button>
    </div>
  );
}
