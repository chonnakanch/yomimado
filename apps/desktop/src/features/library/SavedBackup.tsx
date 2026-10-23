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
        Export all saved words and sentences, including saved translations and
        dates, to a local file. Search filters do not limit the backup.
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
          <ul>
            <li>
              {countLabel(preview.summary.wordsAdded, "new word")} ·{" "}
              {countLabel(preview.summary.wordsSkipped, "duplicate")} skipped
            </li>
            <li>
              {countLabel(preview.summary.sentencesAdded, "new sentence")} ·{" "}
              {countLabel(preview.summary.sentencesSkipped, "duplicate")}{" "}
              skipped
            </li>
          </ul>
          <p className="library-metadata">
            Only missing entries will be added. Existing meanings, translations
            and dates stay unchanged. Duplicate counts may change if you save or
            remove entries before restoring.
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
                      `Restored ${countLabel(result.wordsAdded, "word")} and ${countLabel(result.sentencesAdded, "sentence")}; skipped ${countLabel(result.wordsSkipped + result.sentencesSkipped, "duplicate")}.`,
                    );
                    onRestored();
                    setFocusRestore(true);
                  }
                })
              }
            >
              Restore missing entries
            </button>
            <button
              className="utility-button"
              disabled={busy !== null}
              onClick={cancel}
            >
              Cancel restore
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
      <p className="library-metadata">
        Backups contain your saved text in plain JSON. Screenshots, models,
        settings and translation caches are excluded. Dictionary meanings retain
        their JMdict (EDRDG) · CC BY-SA 4.0 attribution.
      </p>
    </details>
  );
}
