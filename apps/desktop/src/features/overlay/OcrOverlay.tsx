import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import type { CaptureMetadata } from "../../lib/coordinates";
import { ocrPolygonToOverlay } from "../../lib/coordinates";
import type { TextRegion } from "../../lib/ocr-types";

interface OverlayState {
  metadata: CaptureMetadata;
  regions: TextRegion[];
  engine: "demo" | "manga";
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
        if (mounted) setState(overlayState);
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
        {state.regions.some(
          (region) => region.geometrySource === "selection",
        ) && <span className="demo-label">Approximate OCR area</span>}
        {state.regions.some((region) => region.needsReview) && (
          <span className="demo-label">Dashed gold: check OCR text</span>
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
        {state.regions.map((region) => (
          <polygon
            className={`ocr-region${state.engine === "demo" ? " demo" : ""}${region.geometrySource === "selection" ? " approximate" : ""}${region.needsReview ? " needs-review" : ""}${activeRegionId === region.id ? " active" : ""}`}
            key={region.id}
            points={polygonPoints(region, state.metadata, {
              width: contentWidth,
              height: contentHeight,
            })}
            onClick={() => void handleRegionClick(region)}
          >
            <title>{`${region.text} (${region.orientation}${region.geometrySource === "selection" ? ", approximate area" : ""}${region.needsReview ? ", review suggested" : ""})${region.reviewReason ? ` — ${region.reviewReason}` : ""}`}</title>
          </polygon>
        ))}
      </svg>
    </div>
  );
}
