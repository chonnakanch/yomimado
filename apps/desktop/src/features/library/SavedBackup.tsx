import { useEffect, useRef, useState } from "react";
import {
  exportSavedBackup,
  previewSavedBackup,
  restoreSavedBackup,
} from "../../lib/backup-client";

const countLabel = (count: number, noun: string) =>
  `${count} ${noun}${count === 1 ? "" : "s"}`;

export function SavedBackup({ onRestored }: { onRestored: () => void }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [preview, setPreview] =
    useState<Awaited<ReturnType<typeof previewSavedBackup>>>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const pending = useRef(false);
  const mounted = useRef(false);
  const restoreButton = useRef<HTMLButtonElement>(null);
  const confirmButton = useRef<HTMLButtonElement>(null);
  const previewPanel = useRef<HTMLElement>(null);
  const [focusRestore, setFocusRestore] = useState(false);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    if (preview && !busy) {
      if (confirmButton.current?.disabled) previewPanel.current?.focus();
      else confirmButton.current?.focus();
    }
    if (focusRestore && !preview && !busy) {
      restoreButton.current?.focus();
      setFocusRestore(false);
    }
  }, [preview, busy, focusRestore]);

  const run = async (label: string, action: () => Promise<void>) => {
    if (pending.current) return;
    pending.current = true;
    setBusy(label);
    setError(null);
    setStatus("");
    try {
      await action();
    } catch (reason) {
      if (mounted.current) setError(String(reason).replace(/^Error: /, ""));
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(null);
    }
  };
  const cancel = () => {
    setPreview(null);
    setError(null);
    setFocusRestore(true);
  };

  return (
    <details className="library-backup library-context">
      <summary>Backup &amp; restore</summary>
      <p className="library-metadata">
        Back up your saved words and sentences.
      </p>
      <div className="library-backup-actions">
        <button
          className="utility-button"
          disabled={busy !== null || preview !== null}
          onClick={() =>
            void run("Exporting…", async () => {
              const saved = await exportSavedBackup();
              if (mounted.current)
                setStatus(saved ? "Backup saved." : "Export canceled.");
            })
          }
        >
          Export backup
        </button>
        <button
          className="utility-button"
          ref={restoreButton}
          disabled={busy !== null || preview !== null}
          onClick={() =>
            void run("Reading backup…", async () => {
              const result = await previewSavedBackup();
              if (mounted.current) {
                setPreview(result);
                if (!result) setStatus("Restore canceled.");
              }
            })
          }
        >
          Restore backup
        </button>
      </div>
      {preview && (
        <section
          className="library-backup-preview"
          aria-label="Restore preview"
          ref={previewPanel}
          tabIndex={-1}
        >
          <h2>Restore preview</h2>
          <p>{preview.file.name}</p>
          <p>
            {countLabel(preview.summary.wordsAdded, "new word")} ·{" "}
            {countLabel(preview.summary.sentencesAdded, "new sentence")}
          </p>
          <p className="library-metadata">
            {countLabel(
              preview.summary.wordsSkipped + preview.summary.sentencesSkipped,
              "duplicate",
            )}{" "}
            skipped. Existing entries stay unchanged.
          </p>
          <div className="library-backup-actions">
            <button
              className="utility-button"
              ref={confirmButton}
              disabled={
                busy !== null ||
                preview.summary.wordsAdded + preview.summary.sentencesAdded ===
                  0
              }
              onClick={() =>
                void run("Restoring…", async () => {
                  const result = await restoreSavedBackup(preview.file);
                  if (mounted.current) {
                    setPreview(null);
                    setStatus(
                      `Restored ${countLabel(result.wordsAdded, "word")} and ${countLabel(result.sentencesAdded, "sentence")}.`,
                    );
                    onRestored();
                    setFocusRestore(true);
                  }
                })
              }
            >
              Restore
            </button>
            <button
              className="utility-button"
              disabled={busy !== null}
              onClick={cancel}
            >
              Cancel
            </button>
          </div>
          {preview.summary.wordsAdded + preview.summary.sentencesAdded ===
            0 && <p>Nothing new to restore.</p>}
        </section>
      )}
      <p className="library-live-status" role="status">
        {busy ?? status}
      </p>
      {error && (
        <p className="library-error" role="alert">
          {error} Try again.
        </p>
      )}
    </details>
  );
}
