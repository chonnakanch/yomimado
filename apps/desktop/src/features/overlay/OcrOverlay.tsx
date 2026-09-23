import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
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
  const [activeRegionId, setActiveRegionId] = useState<string | null>(null);
  const [viewport, setViewport] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  const state = JSON.parse(
    new URLSearchParams(window.location.search).get("state") ?? "null",
  ) as OverlayState | null;

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        void getCurrentWindow().close();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    const handleResize = () =>
      setViewport({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

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
    await invoke("region_clicked", { regionId: region.id });
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
        <button
          className="close-overlay"
          onClick={() => void getCurrentWindow().close()}
          aria-label="Close overlay"
          title="Close overlay (Esc)"
        >
          ×
        </button>
      </div>
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
            className={`ocr-region${state.engine === "demo" ? " demo" : ""}${activeRegionId === region.id ? " active" : ""}`}
            key={region.id}
            points={polygonPoints(region, state.metadata, {
              width: contentWidth,
              height: contentHeight,
            })}
            onClick={() => void handleRegionClick(region)}
          >
            <title>{`${region.text} (${region.orientation})`}</title>
          </polygon>
        ))}
      </svg>
    </div>
  );
}
