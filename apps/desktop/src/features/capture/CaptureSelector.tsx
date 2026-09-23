import { useEffect, useMemo, useState, type PointerEvent } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { invoke } from "@tauri-apps/api/core";
import { requestOcr } from "../../lib/ocr-client";
import {
  normalizeRectangle,
  type CaptureMetadata,
} from "../../lib/coordinates";
import type { Point } from "../../lib/ocr-types";
import type { OcrResponse } from "../../lib/ocr-types";

interface CaptureResult {
  imagePath: string;
  imageDataUrl: string;
  metadata: CaptureMetadata;
}

export function CaptureSelector() {
  const [start, setStart] = useState<Point | null>(null);
  const [end, setEnd] = useState<Point | null>(null);
  const [error, setError] = useState<string | null>(null);
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

  const point = (event: PointerEvent<HTMLDivElement>): Point => {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    };
  };

  const finish = async (event: PointerEvent<HTMLDivElement>) => {
    if (!start) return;
    const selection = normalizeRectangle(start, point(event));
    if (selection.width < 4 || selection.height < 4) return;
    const viewport = {
      width: event.currentTarget.clientWidth,
      height: event.currentTarget.clientHeight,
    };
    document.documentElement.dataset.capturing = "true";
    try {
      // Let the transparent selector repaint before xcap takes its screenshot.
      await new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      );
      const captured = await invoke<CaptureResult>("capture_selection", {
        selection,
        viewport,
      });
      const response: OcrResponse = await requestOcr(captured.imageDataUrl);
      await invoke("show_ocr_overlay", {
        metadata: captured.metadata,
        regions: response.regions,
        engine: response.engine,
      });
      await getCurrentWindow().close();
    } catch (captureError) {
      document.documentElement.dataset.capturing = "false";
      setError(`Capture or OCR failed: ${String(captureError)}`);
    }
  };

  return (
    <div
      className="capture-selector"
      onPointerDown={(event) => {
        event.currentTarget.setPointerCapture(event.pointerId);
        const next = point(event);
        setStart(next);
        setEnd(next);
      }}
      onPointerMove={(event) => start && setEnd(point(event))}
      onPointerUp={(event) => void finish(event)}
    >
      <p>Drag to capture a region. Press Escape to cancel.</p>
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
