import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import type { CaptureMetadata } from "../../lib/coordinates";
import { ocrPolygonToOverlay } from "../../lib/coordinates";
import type { TextRegion } from "../../lib/ocr-types";

interface OverlayState {
  metadata: CaptureMetadata;
  regions: TextRegion[];
  engine: "demo" | "manga";
  estimatedReadingOrder?: boolean;
  layout: {
    windowWidth: number;
    windowHeight: number;
    contentLeft: number;
    contentTop: number;
    contentWidth: number;
    contentHeight: number;
    toolbarTop: number;
    toolbarHeight: number;
  };
}

function polygonPoints(
  region: TextRegion,
  metadata: CaptureMetadata,
  viewport: { width: number; height: number },
) {
  return ocrPolygonToOverlay(region.polygon, metadata, viewport)
    .map((point) => `${point.x},${point.y}`)
    .join(" ");
}

export function OcrOverlay() {
  const [state, setState] = useState<OverlayState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeRegionId, setActiveRegionId] = useState<string | null>(null);
  const [popupError, setPopupError] = useState<string | null>(null);
  const [viewport, setViewport] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  useEffect(() => {
    let mounted = true;
    void invoke<OverlayState>("get_overlay_state")
      .then((overlayState) => {
        if (mounted) {
          setState(overlayState);
          if (overlayState.estimatedReadingOrder) {
            setActiveRegionId(overlayState.regions[0]?.id ?? null);
          }
        }
      })
      .catch((error) => {
        if (mounted)
          setLoadError(`Could not load OCR overlay: ${String(error)}`);
      });
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        void invoke("close_ocr_overlay");
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    const handleResize = () =>
      setViewport({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", handleResize);
    return () => {
      mounted = false;
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  if (loadError) return <div className="overlay-error">{loadError}</div>;
  if (!state) return null;

  // Convert the native physical layout into this webview's measured CSS size.
  const scaleX =
    (viewport.width * state.metadata.scaleFactor) / state.layout.windowWidth;
  const scaleY =
    (viewport.height * state.metadata.scaleFactor) / state.layout.windowHeight;
  const contentWidth = state.layout.contentWidth * scaleX;
  const contentHeight = state.layout.contentHeight * scaleY;
  const selectedRegionIndex = state.regions.findIndex(
    (region) => region.id === activeRegionId,
  );
  const activeRegionIndex = Math.max(0, selectedRegionIndex);

  const moveReadingOrder = (direction: number) => {
    const count = state.regions.length;
    if (!count) return;
    const nextIndex = (activeRegionIndex + direction + count) % count;
    setActiveRegionId(state.regions[nextIndex].id);
  };

  const handleRegionClick = async (region: TextRegion) => {
    setActiveRegionId(region.id);
    setPopupError(null);
    try {
      await invoke("show_translation_popup", {
        metadata: state.metadata,
        text: region.text,
        polygon: region.polygon,
        demo: state.engine === "demo",
      });
    } catch (error) {
      setPopupError(String(error));
    }
  };

  return (
    <div className="ocr-overlay">
      <div
        className="overlay-toolbar"
        style={{
          top: state.layout.toolbarTop * scaleY,
          height: state.layout.toolbarHeight * scaleY,
        }}
      >
        {state.engine === "demo" && (
          <span className="demo-label">Demo area</span>
        )}
        {state.regions.some((region) => region.geometrySource != null) && (
          <span className="demo-label">Approximate OCR area</span>
        )}
        {state.regions.some((region) => region.needsReview) && (
          <span className="demo-label">Dashed gold: check OCR text</span>
        )}
        {state.estimatedReadingOrder && state.regions.length > 0 && (
          <div
            className="overlay-reading-order"
            aria-label="Estimated manga reading order"
          >
            <button
              aria-label="Previous text region"
              onClick={() => moveReadingOrder(-1)}
            >
              ‹
            </button>
            <span
              aria-live="polite"
              title="Estimated from text positions; click any region to correct the sequence"
            >
              Est. {activeRegionIndex + 1}/{state.regions.length} ·{" "}
              {state.regions[activeRegionIndex]?.text}
            </span>
            <button
              aria-label="Next text region"
              onClick={() => moveReadingOrder(1)}
            >
              ›
            </button>
            <button
              aria-label="Open selected text region"
              onClick={() =>
                void handleRegionClick(state.regions[activeRegionIndex])
              }
            >
              Open
            </button>
          </div>
        )}
        <button
          className="close-overlay"
          onClick={() => void invoke("close_ocr_overlay")}
          aria-label="Close overlay"
          title="Close overlay (Esc)"
        >
          ×
        </button>
      </div>
      {popupError && <div className="overlay-error">{popupError}</div>}
      <svg
        style={{
          left: state.layout.contentLeft * scaleX,
          top: state.layout.contentTop * scaleY,
          width: contentWidth,
          height: contentHeight,
        }}
        aria-label="OCR regions"
      >
        {state.regions.map((region, index) => (
          <polygon
            className={`ocr-region${state.engine === "demo" ? " demo" : ""}${region.geometrySource ? " approximate" : ""}${region.needsReview ? " needs-review" : ""}${activeRegionId === region.id ? " active" : ""}`}
            key={region.id}
            points={polygonPoints(region, state.metadata, {
              width: contentWidth,
              height: contentHeight,
            })}
            onClick={() => void handleRegionClick(region)}
          >
            <title>{`${state.estimatedReadingOrder ? `${index + 1}. ` : ""}${region.text} (${region.orientation}${region.geometrySource ? ", approximate area" : ""}${region.needsReview ? ", review suggested" : ""})${region.reviewReason ? ` — ${region.reviewReason}` : ""}`}</title>
          </polygon>
        ))}
      </svg>
    </div>
  );
}
