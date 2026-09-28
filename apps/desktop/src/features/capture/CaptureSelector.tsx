import { useEffect, useMemo, useRef, useState, type PointerEvent } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { invoke } from "@tauri-apps/api/core";
import { requestOcr } from "../../lib/ocr-client";
import {
  normalizeRectangle,
  type CaptureMetadata,
} from "../../lib/coordinates";
import type { Point } from "../../lib/ocr-types";
import type { OcrResponse } from "../../lib/ocr-types";
import { CaptureDebugView } from "./CaptureDebugView";

interface CaptureResult {
  imageDataUrl: string;
  metadata: CaptureMetadata;
}

const debugCaptureEnabled = import.meta.env.VITE_CAPTURE_DEBUG === "1";

export function CaptureSelector() {
  const scanDisplay =
    new URLSearchParams(window.location.search).get("scan") === "display";
  const [start, setStart] = useState<Point | null>(null);
  const [end, setEnd] = useState<Point | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [debugCapture, setDebugCapture] = useState<{
    captured: CaptureResult;
    response: OcrResponse | null;
    error: string | null;
  } | null>(null);
  const captureStarted = useRef(false);
  const selection = useMemo(
    () => (start && end ? normalizeRectangle(start, end) : null),
    [start, end],
  );

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        void invoke("cancel_capture_selector");
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (!scanDisplay || captureStarted.current) return;
    captureStarted.current = true;
    void captureAndRecognize(() => invoke<CaptureResult>("capture_display"));
  }, []);

  const point = (event: PointerEvent<HTMLDivElement>): Point => {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    };
  };

  const showOverlay = async (
    captured: CaptureResult,
    response: OcrResponse,
  ) => {
    await invoke("show_ocr_overlay", {
      metadata: captured.metadata,
      regions: response.regions,
      engine: response.engine,
    });
    await getCurrentWindow().close();
  };

  const captureAndRecognize = async (capture: () => Promise<CaptureResult>) => {
    document.documentElement.dataset.capturing = "true";
    try {
      // Let the transparent selector repaint before xcap takes its screenshot.
      await new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      );
      const captured = await capture();
      if (debugCaptureEnabled) {
        setDebugCapture({ captured, response: null, error: null });
        document.documentElement.dataset.capturing = "false";
      }
      const response: OcrResponse = await requestOcr(captured.imageDataUrl, {
        debug: debugCaptureEnabled,
      });
      if (debugCaptureEnabled) {
        setDebugCapture({ captured, response, error: null });
      } else if (scanDisplay && response.engine === "demo") {
        document.documentElement.dataset.capturing = "false";
        setError(
          "Display scanning needs the local OCR models. Press Escape to close.",
        );
      } else if (response.regions.length === 0) {
        document.documentElement.dataset.capturing = "false";
        setError(
          "No text was detected on this display. Press Escape to close.",
        );
      } else {
        await showOverlay(captured, response);
      }
    } catch (captureError) {
      document.documentElement.dataset.capturing = "false";
      const message = `Capture or OCR failed: ${String(captureError)}`;
      setDebugCapture((current) =>
        current ? { ...current, error: message } : null,
      );
      setError(message);
    }
  };

  const finish = async (event: PointerEvent<HTMLDivElement>) => {
    if (!start || captureStarted.current) return;
    const selection = normalizeRectangle(start, point(event));
    if (selection.width < 4 || selection.height < 4) return;
    captureStarted.current = true;
    const viewport = {
      width: event.currentTarget.clientWidth,
      height: event.currentTarget.clientHeight,
    };
    await captureAndRecognize(() =>
      invoke<CaptureResult>("capture_selection", { selection, viewport }),
    );
    captureStarted.current = false;
  };

  if (debugCapture) {
    return (
      <CaptureDebugView
        imageDataUrl={debugCapture.captured.imageDataUrl}
        metadata={debugCapture.captured.metadata}
        response={debugCapture.response}
        error={debugCapture.error}
        onContinue={() => {
          if (!debugCapture.response) return;
          void showOverlay(debugCapture.captured, debugCapture.response).catch(
            (overlayError) =>
              setDebugCapture((current) =>
                current
                  ? {
                      ...current,
                      error: `Overlay failed: ${String(overlayError)}`,
                    }
                  : null,
              ),
          );
        }}
        onCancel={() => void invoke("cancel_capture_selector")}
      />
    );
  }

  return (
    <div
      className="capture-selector"
      onPointerDown={
        scanDisplay
          ? undefined
          : (event) => {
              event.currentTarget.setPointerCapture(event.pointerId);
              const next = point(event);
              setStart(next);
              setEnd(next);
            }
      }
      onPointerMove={
        scanDisplay ? undefined : (event) => start && setEnd(point(event))
      }
      onPointerUp={scanDisplay ? undefined : (event) => void finish(event)}
    >
      <p>
        {scanDisplay
          ? "Scanning this display… Press Escape to cancel."
          : "Drag to capture a region. Press Escape to cancel."}
      </p>
      {error && <p className="capture-error">{error}</p>}
      {selection && (
        <div
          className="selection"
          style={{
            left: `${selection.x}px`,
            top: `${selection.y}px`,
            width: `${selection.width}px`,
            height: `${selection.height}px`,
          }}
        />
      )}
    </div>
  );
}
