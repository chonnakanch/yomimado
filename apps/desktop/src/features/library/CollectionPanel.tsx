import { useEffect, useState } from "react";

export function CollectionFeedback({
  loading,
  error,
  empty,
  removed,
  kind,
  onRetry,
}: {
  loading: boolean;
  error: string | null;
  empty: boolean;
  removed: boolean;
  kind: "words" | "sentences";
  onRetry: () => void;
}) {
  return (
    <>
      <div className="library-live-status" role="status">
        {loading
          ? `Loading saved ${kind}…`
          : removed
            ? `Removed from saved ${kind}.`
            : ""}
      </div>
      {error && (
        <div className="library-error" role="alert">
          <p>{error}</p>
          <button className="utility-button" onClick={onRetry}>
            Retry loading {kind}
          </button>
        </div>
      )}
      {!loading && !error && empty && (
        <div className="library-empty">
          <h3>No saved {kind} yet</h3>
          <p>
            {kind === "words"
              ? "Choose a word in the learning popup to save it."
              : "Save a Japanese sentence in the learning popup."}
          </p>
        </div>
      )}
    </>
  );
}

export function SavedDate({ value }: { value: string }) {
  const date = new Date(value);
  return (
    <p className="library-date">
      Saved{" "}
      {Number.isNaN(date.getTime()) ? (
        "date unavailable"
      ) : (
        <time dateTime={date.toISOString()}>{date.toLocaleString()}</time>
      )}
    </p>
  );
}

export function useRemovalFocus() {
  const [restore, setRestore] = useState<{
    panel: HTMLElement;
    origin: HTMLButtonElement;
    target: HTMLButtonElement;
  } | null>(null);
  useEffect(() => {
    if (!restore) return;
    if (
      !restore.panel.hidden &&
      restore.target.isConnected &&
      (document.activeElement === document.body ||
        document.activeElement === restore.origin)
    )
      restore.target.focus();
    setRestore(null);
  }, [restore]);

  return async (origin: HTMLButtonElement, remove: () => Promise<boolean>) => {
    const panel = origin.closest<HTMLElement>('[role="tabpanel"]');
    const ownedFocus = document.activeElement === origin;
    const buttons = Array.from(
      panel?.querySelectorAll<HTMLButtonElement>("[data-remove]") ?? [],
    );
    const index = buttons.indexOf(origin);
    const target =
      buttons[index + 1] ??
      buttons[index - 1] ??
      panel?.querySelector<HTMLButtonElement>("[data-refresh]");
    if ((await remove()) && ownedFocus && panel && target)
      setRestore({ panel, origin, target });
  };
}
