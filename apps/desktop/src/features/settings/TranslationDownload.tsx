import { useEffect, useState } from "react";
import { requestService } from "../../lib/service-client";

interface ModelStatus {
  state: "notInstalled" | "downloading" | "ready" | "error" | "unavailable";
  receivedBytes: number;
  downloadBytes: number;
  error: string | null;
}

async function requestStatus(install = false): Promise<ModelStatus> {
  const response = await requestService(
    `/api/v1/translation-model${install ? "/install" : ""}`,
    "Translation setup",
    install ? { method: "POST" } : undefined,
  );
  const value: unknown = await response.json();
  if (
    !value ||
    typeof value !== "object" ||
    !("state" in value) ||
    typeof value.state !== "string" ||
    !["notInstalled", "downloading", "ready", "error", "unavailable"].includes(
      value.state,
    ) ||
    !("receivedBytes" in value) ||
    typeof value.receivedBytes !== "number" ||
    !Number.isSafeInteger(value.receivedBytes) ||
    value.receivedBytes < 0 ||
    !("downloadBytes" in value) ||
    typeof value.downloadBytes !== "number" ||
    !Number.isSafeInteger(value.downloadBytes) ||
    value.downloadBytes < 0 ||
    !("error" in value) ||
    (value.error !== null && typeof value.error !== "string")
  )
    throw new Error("Translation setup returned an invalid status");
  return value as ModelStatus;
}

export function TranslationDownload({ active }: { active: boolean }) {
  const [status, setStatus] = useState<ModelStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const refresh = async () => {
      try {
        const result = await requestStatus();
        if (cancelled) return;
        setStatus(result);
        setError(null);
        if (result.state === "downloading") timer = setTimeout(refresh, 1000);
      } catch (reason) {
        if (!cancelled)
          setError(
            reason instanceof Error
              ? reason.message
              : "Could not check translation setup",
          );
      }
    };
    void refresh();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [active, starting, refreshKey]);
  const download = async () => {
    setStarting(true);
    setError(null);
    try {
      setStatus(await requestStatus(true));
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Could not start download",
      );
    } finally {
      setStarting(false);
    }
  };
  const busy = starting || status?.state === "downloading";
  return (
    <div className="settings-card">
      <h2>Local translation</h2>
      <p>
        Download the optional Japanese-to-English model once. Translation then
        works offline when you request it. Your text and screenshots stay on
        this computer.
      </p>
      <p role="status">
        {status?.state === "ready"
          ? "Ready for offline translation."
          : busy
            ? "Downloading local translation…"
            : status?.state === "unavailable"
              ? "A translation download is not configured in this build."
              : status
                ? `Not installed. Download size: ${Math.ceil(status.downloadBytes / 1024 / 1024)} MiB.`
                : "Checking translation setup…"}
      </p>
      {status?.state === "downloading" && (
        <progress
          aria-label="Translation model download"
          max={status.downloadBytes}
          value={status.receivedBytes}
        />
      )}
      {(error || status?.error) && (
        <p className="settings-error" role="alert">
          {error || status?.error}
        </p>
      )}
      {status && status.state !== "ready" && status.state !== "unavailable" && (
        <button
          className="utility-button"
          disabled={busy}
          onClick={() => void download()}
        >
          {busy
            ? "Downloading…"
            : status.state === "error"
              ? "Retry download"
              : "Download local translation"}
        </button>
      )}
      {error && !busy && (
        <button
          className="utility-button"
          onClick={() => setRefreshKey((value) => value + 1)}
        >
          Check again
        </button>
      )}
    </div>
  );
}
