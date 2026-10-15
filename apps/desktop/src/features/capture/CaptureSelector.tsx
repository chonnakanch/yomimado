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
import { orderMangaRegions } from "./reading-order";
import {
  loadScanArea,
  physicalToSelection,
  saveScanArea,
  selectionToPhysical,
  type CaptureSurface,
} from "./scan-area";

interface CaptureResult {
  imageDataUrl: string;
  metadata: CaptureMetadata;
}

export function CaptureSelector() {
  const debugCaptureEnabled = import.meta.env.VITE_CAPTURE_DEBUG === "1";
  const params = new URLSearchParams(window.location.search);
  const scanMode = params.get("scan");
  const sessionId = params.has("session")
    ? Number(params.get("session"))
    : null;
  const invokeCapture = <T,>(
    command: string,
    args?: Record<string, unknown>,
  ) =>
    sessionId !== null
      ? invoke<T>(command, { ...args, sessionId })
      : args
        ? invoke<T>(command, args)
        : invoke<T>(command);
  const automaticScan = scanMode === "auto" || scanMode === "whole";
  const scanArea = automaticScan || scanMode === "configure";
  const estimatedOrder =
    scanArea || scanMode === "whole" || params.get("order") === "1";
  const [start, setStart] = useState<Point | null>(null);
  const [end, setEnd] = useState<Point | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [needsArea, setNeedsArea] = useState(scanMode === "configure");
  const [scanSource, setScanSource] = useState<
    "automatic" | "saved" | "manual"
  >("manual");
  const [debugCapture, setDebugCapture] = useState<{
    captured: CaptureResult;
    response: OcrResponse | null;
    error: string | null;
  } | null>(null);
  const captureStarted = useRef(false);
  const scanChecked = useRef(false);
  const selection = useMemo(
    () => (start && end ? normalizeRectangle(start, end) : null),
    [start, end],
  );

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        void invokeCapture("cancel_capture_selector");
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (
      !["auto", "whole", "repeat"].includes(scanMode ?? "") ||
      scanChecked.current
    )
      return;
    scanChecked.current = true;
    void (async () => {
      captureStarted.current = true;
      await captureAndRecognize(async () => {
        if (scanMode === "repeat")
          return invokeCapture<CaptureResult>("capture_repeat_scan");
        const automatic = await invokeCapture<CaptureResult | null>(
          scanMode === "whole" ? "capture_whole_screen" : "capture_auto_page",
        );
        if (automatic) {
          setScanSource("automatic");
          return automatic;
        }
        const surface = await invokeCapture<CaptureSurface>(
          "get_capture_surface",
        );
        const viewport = {
          width: document.documentElement.clientWidth,
          height: document.documentElement.clientHeight,
        };
        const area = loadScanArea(surface);
        const selection = area && physicalToSelection(area, viewport, surface);
        if (!selection) {
          setError(
            "Automatic page detection was uncertain. Drag around the manga area to save it for future scans.",
          );
          setNeedsArea(true);
          return null;
        }
        setScanSource("saved");
        return invokeCapture<CaptureResult>("capture_selection", {
          selection,
          viewport,
        });
      });
      captureStarted.current = false;
    })();
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
    await invokeCapture("show_ocr_overlay", {
      metadata: captured.metadata,
      regions: response.regions,
      engine: response.engine,
      estimatedReadingOrder: estimatedOrder && response.engine === "manga",
    });
    if (sessionId !== null) {
      await invoke("hide_finished_selector", { sessionId });
    } else {
      await getCurrentWindow().close();
    }
  };

  const captureAndRecognize = async (
    capture: () => Promise<CaptureResult | null>,
  ) => {
    document.documentElement.dataset.capturing = "true";
    let canReviewDebugCapture = false;
    try {
      // Let the transparent selector repaint before xcap takes its screenshot.
      // WebView2 may suspend animation frames while this newly created window
      // is hidden or transparent. Native capture also waits for the compositor;
      // a missed browser frame must not leave automatic scanning stuck forever.
      await new Promise<void>((resolve) => {
        const repaintDeadline = window.setTimeout(resolve, 100);
        requestAnimationFrame(() =>
          requestAnimationFrame(() => {
            window.clearTimeout(repaintDeadline);
            resolve();
          }),
        );
      });
      const captured = await capture();
      if (!captured) {
        document.documentElement.dataset.capturing = "false";
        if (sessionId !== null)
          await invoke("resume_capture_selection", { sessionId, debug: false });
        return;
      }
      if (debugCaptureEnabled) {
        canReviewDebugCapture = true;
        setDebugCapture({ captured, response: null, error: null });
        document.documentElement.dataset.capturing = "false";
        if (sessionId !== null)
          await invoke("resume_capture_selection", { sessionId, debug: true });
      }
      const rawResponse: OcrResponse = await requestOcr(captured.imageDataUrl, {
        debug: debugCaptureEnabled,
      });
      const response =
        estimatedOrder && rawResponse.engine === "manga"
          ? {
              ...rawResponse,
              regions: orderMangaRegions(rawResponse.regions),
            }
          : rawResponse;
      if (debugCaptureEnabled) {
        setDebugCapture({ captured, response, error: null });
      } else if (scanArea && response.engine === "demo") {
        document.documentElement.dataset.capturing = "false";
        setError(
          "Area scanning needs the local OCR models. Press Escape to close.",
        );
        if (sessionId !== null)
          await invoke("finish_scan", {
            sessionId,
            message:
              "Scanning needs the local OCR models. Configure them before retrying.",
          });
      } else if (response.regions.length === 0) {
        document.documentElement.dataset.capturing = "false";
        if (automaticScan) setNeedsArea(true);
        setError(
          `No text was detected in this ${scanArea ? "scan area" : "selection"}. ${automaticScan ? "Drag a reading area to retry, or press Escape to close." : "Press Escape to close."}`,
        );
        if (sessionId !== null)
          await invoke("finish_scan", {
            sessionId,
            message:
              "No text was detected. Try Selected Area or rescan the previous area.",
            noText: true,
          });
      } else {
        await showOverlay(captured, response);
      }
    } catch (captureError) {
      document.documentElement.dataset.capturing = "false";
      if (automaticScan) setNeedsArea(true);
      const message = `Capture or OCR failed: ${String(captureError)}`;
      setDebugCapture((current) =>
        current ? { ...current, error: message } : null,
      );
      setError(message);
      if (sessionId !== null) {
        const recovery = canReviewDebugCapture
          ? invoke("resume_capture_selection", { sessionId, debug: true })
          : invoke("finish_scan", { sessionId, message });
        await recovery.catch((failure) => {
          console.error("YomiMado: could not finish failed scan", failure);
        });
      }
    }
  };

  const finish = async (event: PointerEvent<HTMLDivElement>) => {
    if (!start || captureStarted.current) return;
    const selection = normalizeRectangle(start, point(event));
    if (selection.width < 4 || selection.height < 4) return;
    setError(null);
    captureStarted.current = true;
    const viewport = {
      width: event.currentTarget.clientWidth,
      height: event.currentTarget.clientHeight,
    };
    if (scanArea) {
      try {
        const surface = await invokeCapture<CaptureSurface>(
          "get_capture_surface",
        );
        const physical = selectionToPhysical(selection, viewport, surface);
        if (!physical) {
          setError(
            "Scan area must fit inside the visible display. Drag again.",
          );
          captureStarted.current = false;
          return;
        }
        saveScanArea(surface, physical);
        setScanSource("saved");
      } catch (saveError) {
        setError(`Unable to save scan area: ${String(saveError)}`);
        captureStarted.current = false;
        return;
      }
    }
    await captureAndRecognize(() =>
      invokeCapture<CaptureResult>("capture_selection", {
        selection,
        viewport,
      }),
    );
    captureStarted.current = false;
  };

  if (debugCapture) {
    return (
      <CaptureDebugView
        imageDataUrl={debugCapture.captured.imageDataUrl}
        metadata={debugCapture.captured.metadata}
        scanSource={scanSource}
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
        onCancel={() => void invokeCapture("cancel_capture_selector")}
      />
    );
  }

  return (
    <div
      className="capture-selector"
      onPointerDown={
        automaticScan && !needsArea
          ? undefined
          : (event) => {
              event.currentTarget.setPointerCapture(event.pointerId);
              const next = point(event);
              setStart(next);
              setEnd(next);
            }
      }
      onPointerMove={
        automaticScan && !needsArea
          ? undefined
          : (event) => start && setEnd(point(event))
      }
      onPointerUp={
        automaticScan && !needsArea ? undefined : (event) => void finish(event)
      }
    >
      <p>
        {scanMode === "repeat"
          ? "Capturing and recognizing Japanese text…"
          : automaticScan && !needsArea
            ? "Finding the manga page… Press Escape to cancel."
            : scanArea
              ? "Drag around the manga reading area. It will be reused on future scans. Press Escape to cancel."
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
