import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { OCRBoundingBox, regionLabel } from "./OCRBoundingBox";
import "./overlay.css";
import type { CaptureMetadata } from "../../lib/coordinates";
import { ocrPolygonToOverlay } from "../../lib/coordinates";
import type { TextRegion } from "../../lib/ocr-types";
import {
  readReadingOrderEnabled,
  readingOrderSettingKey,
} from "../../lib/reading-order-setting";

interface OverlayState {
  sessionId?: number;
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
  const [readingOrderEnabled, setReadingOrderEnabled] = useState(
    readReadingOrderEnabled,
  );
  const [popupError, setPopupError] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);
  const controlsRef = useRef<HTMLDivElement>(null);
  const regionElements = useRef(new Map<string, SVGPolygonElement>());
  const [focusRequest, setFocusRequest] = useState<{
    regionId: string | null;
    revision: number;
  } | null>(null);
  const controlRevision = useRef(0);
  const viewQuery = useRef(window.location.search.slice(1)).current;
  const [viewport, setViewport] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  useEffect(() => {
    const handleSettingChange = (event: StorageEvent) => {
      if (event.key !== null && event.key !== readingOrderSettingKey) return;
      const enabled = readReadingOrderEnabled();
      setReadingOrderEnabled(enabled);
      if (!enabled) {
        setActiveRegionId(null);
      }
    };
    window.addEventListener("storage", handleSettingChange);
    return () => window.removeEventListener("storage", handleSettingChange);
  }, []);

  useEffect(() => {
    let mounted = true;
    void invoke<OverlayState>("get_overlay_state")
      .then((overlayState) => {
        if (mounted) {
          setState(overlayState);
        }
      })
      .catch((error) => {
        if (mounted)
          setLoadError(`Could not load OCR overlay: ${String(error)}`);
      });
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        void invoke("hide_focused_overlay").catch((error) =>
          setPopupError(String(error)),
        );
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

  useEffect(() => {
    if (state?.sessionId === undefined) return;
    let mounted = true;
    void invoke<OverlayState["layout"] | null>("reveal_ocr_overlay", {
      sessionId: state.sessionId,
    })
      .then((layout) => {
        if (mounted && layout) {
          setState((current) => (current ? { ...current, layout } : current));
          setViewport({ width: window.innerWidth, height: window.innerHeight });
          setRevealed(true);
        }
      })
      .catch((error) => {
        if (mounted)
          setLoadError(`Could not display OCR overlay: ${String(error)}`);
      });
    return () => {
      mounted = false;
    };
  }, [state?.sessionId]);

  useEffect(() => {
    if (state?.sessionId === undefined || !revealed) return;
    const update = () => {
      const rectangles = Array.from(
        controlsRef.current?.querySelectorAll<HTMLElement>(
          "button, .overlay-reading-order-panel",
        ) ?? [],
      )
        .filter(
          (element) =>
            !element.closest(".overlay-reading-order-panel") ||
            element.classList.contains("overlay-reading-order-panel"),
        )
        .map((element) => {
          const bounds = element.getBoundingClientRect();
          return {
            x: bounds.x,
            y: bounds.y,
            width: bounds.width,
            height: bounds.height,
          };
        })
        .filter((bounds) => bounds.width > 0 && bounds.height > 0);
      void invoke("update_overlay_controls", {
        sessionId: state.sessionId,
        revision: ++controlRevision.current,
        rectangles,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        viewQuery,
      }).catch((error) =>
        setLoadError(`Could not route overlay input: ${String(error)}`),
      );
    };
    const observer =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(update);
    if (controlsRef.current) observer?.observe(controlsRef.current);
    const panel = controlsRef.current?.querySelector(
      ".overlay-reading-order-panel",
    );
    if (panel) observer?.observe(panel);
    update();
    return () => observer?.disconnect();
  }, [
    state?.sessionId,
    revealed,
    readingOrderEnabled,
    viewport,
    activeRegionId,
  ]);

  useEffect(() => {
    let mounted = true;
    let unlisten: UnlistenFn | undefined;
    void listen<{ regionId: string | null }>("focus-ocr-region", (event) => {
      if (mounted)
        setFocusRequest((previous) => ({
          regionId: event.payload.regionId,
          revision: (previous?.revision ?? 0) + 1,
        }));
    })
      .then((stop) => {
        if (mounted) unlisten = stop;
        else stop();
      })
      .catch((error) => {
        if (mounted)
          setPopupError(
            `Keyboard region access is unavailable: ${String(error)}`,
          );
      });
    return () => {
      mounted = false;
      unlisten?.();
    };
  }, []);

  useEffect(() => {
    if (!focusRequest || !state || (state.sessionId !== undefined && !revealed))
      return;
    const regionId =
      focusRequest.regionId ?? activeRegionId ?? state.regions[0]?.id;
    if (regionId && regionElements.current.has(regionId)) {
      setActiveRegionId(regionId);
      regionElements.current.get(regionId)?.focus();
    }
    // A focus request is explicit; loading and hover must never steal focus.
  }, [focusRequest, state?.sessionId, revealed]);

  if (loadError) return <div className="overlay-error">{loadError}</div>;
  if (!state) return null;

  // Convert the native physical layout into this webview's measured CSS size.
  const scaleX =
    (viewport.width * state.metadata.scaleFactor) / state.layout.windowWidth;
  const scaleY =
    (viewport.height * state.metadata.scaleFactor) / state.layout.windowHeight;
  const contentWidth = state.layout.contentWidth * scaleX;
  const contentHeight = state.layout.contentHeight * scaleY;
  const selectedRegionId =
    activeRegionId ??
    (state.estimatedReadingOrder && readingOrderEnabled
      ? state.regions[0]?.id
      : null);
  const selectedRegionIndex = state.regions.findIndex(
    (region) => region.id === selectedRegionId,
  );
  const activeRegionIndex = Math.max(0, selectedRegionIndex);
  const selectedRegion = state.regions.find(
    (region) => region.id === activeRegionId,
  );

  const moveReadingOrder = (direction: number) => {
    const count = state.regions.length;
    if (!count) return;
    const nextIndex = (activeRegionIndex + direction + count) % count;
    setActiveRegionId(state.regions[nextIndex].id);
  };

  const handleRegionClick = async (region: TextRegion, keyboard = false) => {
    setActiveRegionId(region.id);
    setPopupError(null);
    try {
      await invoke("show_translation_popup", {
        metadata: state.metadata,
        text: region.text,
        polygon: region.polygon,
        demo: state.engine === "demo",
        regionId: region.id,
        ...(state.sessionId !== undefined
          ? { sessionId: state.sessionId }
          : {}),
        keyboard,
      });
    } catch (error) {
      setPopupError(String(error));
    }
  };

  return (
    <div className="ocr-overlay">
      <div
        className="overlay-controls"
        ref={controlsRef}
        style={{
          top: state.layout.toolbarTop * scaleY,
          height: state.layout.toolbarHeight * scaleY,
        }}
      >
        {state.estimatedReadingOrder &&
          readingOrderEnabled &&
          state.regions.length > 0 && (
            <div
              className="overlay-reading-order-panel"
              aria-label="Estimated manga reading order"
            >
              <div className="overlay-reading-order-nav">
                <button
                  aria-label="Previous text region"
                  onClick={() => moveReadingOrder(-1)}
                >
                  ‹
                </button>
                <span className="overlay-reading-order-count">
                  {activeRegionIndex + 1}/{state.regions.length} · estimated
                </span>
                <button
                  aria-label="Next text region"
                  onClick={() => moveReadingOrder(1)}
                >
                  ›
                </button>
                <button
                  aria-label="Open selected text region"
                  onClick={(event) =>
                    void handleRegionClick(
                      state.regions[activeRegionIndex],
                      event.detail === 0,
                    )
                  }
                >
                  Open
                </button>
              </div>
              <p className="overlay-reading-order-text" aria-live="polite">
                {state.regions[activeRegionIndex]?.text}
              </p>
            </div>
          )}
      </div>
      <p className="visually-hidden" id="region-navigation-help">
        Use arrow keys to move between text regions, Enter or Space to open, and
        Escape to hide OCR overlays. Navigation follows detected regions;
        estimated reading order is optional.
      </p>
      <p className="visually-hidden" role="status">
        {selectedRegion
          ? regionLabel(selectedRegion, state.engine === "demo")
          : "Select a region to open its learning popup."}
      </p>
      {popupError && <div className="overlay-error">{popupError}</div>}
      <svg
        style={{
          left: state.layout.contentLeft * scaleX,
          top: state.layout.contentTop * scaleY,
          width: contentWidth,
          height: contentHeight,
          visibility:
            state.sessionId !== undefined && !revealed ? "hidden" : undefined,
        }}
        aria-label="OCR regions"
        aria-describedby="region-navigation-help"
      >
        {state.regions.map((region, index) => (
          <OCRBoundingBox
            region={region}
            demo={state.engine === "demo"}
            selected={selectedRegionId === region.id}
            tabIndex={index === activeRegionIndex ? 0 : -1}
            number={
              state.estimatedReadingOrder && readingOrderEnabled
                ? index + 1
                : undefined
            }
            elementRef={(element) => {
              if (element) regionElements.current.set(region.id, element);
              else regionElements.current.delete(region.id);
            }}
            onFocus={() => setActiveRegionId(region.id)}
            onActivate={(keyboard) => void handleRegionClick(region, keyboard)}
            onNavigate={(key) => {
              const nextIndex =
                key === "Home"
                  ? 0
                  : key === "End"
                    ? state.regions.length - 1
                    : (index +
                        (["ArrowDown", "ArrowRight"].includes(key) ? 1 : -1) +
                        state.regions.length) %
                      state.regions.length;
              const next = state.regions[nextIndex];
              setActiveRegionId(next.id);
              regionElements.current.get(next.id)?.focus();
            }}
            key={region.id}
            points={polygonPoints(region, state.metadata, {
              width: contentWidth,
              height: contentHeight,
            })}
          />
        ))}
      </svg>
    </div>
  );
}
