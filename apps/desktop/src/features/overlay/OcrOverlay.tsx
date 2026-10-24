import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { OCRBoundingBox, regionLabel } from "./OCRBoundingBox";
import { ToolbarIcon } from "../toolbar/ToolbarIcon";
import "./overlay.css";
import type { CaptureMetadata } from "../../lib/coordinates";
import { ocrPolygonToOverlay } from "../../lib/coordinates";
import type { TextRegion } from "../../lib/ocr-types";
import { BubbleTranslation } from "./BubbleTranslation";
import { availableTranslationBounds } from "./translation-layout";
import {
  bubbleTranslationRegions,
  useBubbleTranslations,
} from "./useBubbleTranslations";

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
  const [popupError, setPopupError] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [hiding, setHiding] = useState(false);
  const hideButton = useRef<HTMLButtonElement>(null);
  const translationControls = useRef<HTMLDivElement>(null);
  const translationElements = useRef(new Map<string, HTMLDivElement>());
  const [translationEnabled, setTranslationEnabled] = useState(false);
  const [translationAttempt, setTranslationAttempt] = useState(0);
  const translatable = useMemo(
    () =>
      state?.engine === "manga" ? bubbleTranslationRegions(state.regions) : [],
    [state?.regions, state?.engine],
  );
  const {
    translations,
    pending,
    error: translationError,
  } = useBubbleTranslations(
    translatable,
    translationEnabled,
    translationAttempt,
  );
  const controlRevision = useRef(0);
  const hidePending = useRef(false);
  const navigatorRef = useRef<HTMLDivElement>(null);
  const regionElements = useRef(new Map<string, SVGPolygonElement>());
  const [focusRequest, setFocusRequest] = useState<{
    regionId: string | null;
    revision: number;
  } | null>(null);
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
        }
      })
      .catch((error) => {
        if (mounted)
          setLoadError(`Could not load OCR overlay: ${String(error)}`);
      });
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setTranslationEnabled(false);
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
    const button = hideButton.current;
    if (!button) return;
    let mounted = true;
    const report = () => {
      const elements = [
        button,
        translationControls.current,
        ...translationElements.current.values(),
      ].filter((element) => element !== null);
      const rectangles = elements
        .map((element) => element.getBoundingClientRect())
        .filter((rect) => rect.width > 0 && rect.height > 0)
        .map(({ x, y, width, height }) => ({ x, y, width, height }));
      if (!rectangles.length) return;
      void invoke("update_overlay_controls", {
        sessionId: state.sessionId,
        revision: ++controlRevision.current,
        rectangles,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        viewQuery: window.location.search.slice(1),
      }).catch((error) => {
        if (mounted)
          setPopupError(`Could not enable overlay controls: ${String(error)}`);
      });
    };
    const observer =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(report);
    observer?.observe(button);
    if (translationControls.current)
      observer?.observe(translationControls.current);
    for (const element of translationElements.current.values())
      observer?.observe(element);
    report();
    return () => {
      mounted = false;
      observer?.disconnect();
    };
  }, [
    state?.sessionId,
    state?.layout,
    revealed,
    viewport.width,
    viewport.height,
    translationEnabled,
    translations,
    pending,
    translationError,
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
    let mounted = true;
    let unlisten: UnlistenFn | undefined;
    void listen("stop-bubble-translations", () => {
      if (mounted) setTranslationEnabled(false);
    })
      .then((stop) => {
        if (mounted) unlisten = stop;
        else stop();
      })
      .catch((error) => {
        if (mounted)
          setPopupError(
            `Translation lifecycle events unavailable: ${String(error)}`,
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
      focusRegion(regionId);
    }
    // A focus request is explicit; loading and hover must never steal focus.
  }, [focusRequest, state?.sessionId, revealed]);

  const focusRegion = (regionId: string) => {
    setActiveRegionId(regionId);
    const element = regionElements.current.get(regionId);
    element?.focus?.();
    // SVG focus support varies between webviews. Keep a real HTML focus target
    // so native keyboard entry still works when polygon.focus() does not.
    if (document.activeElement !== element) navigatorRef.current?.focus();
  };
  const navigateRegion = (key: string, current: number) => {
    if (!state?.regions.length) return;
    const nextIndex =
      key === "Home"
        ? 0
        : key === "End"
          ? state.regions.length - 1
          : (current +
              (["ArrowDown", "ArrowRight"].includes(key) ? 1 : -1) +
              state.regions.length) %
            state.regions.length;
    focusRegion(state.regions[nextIndex].id);
  };

  if (loadError) return <div className="overlay-error">{loadError}</div>;
  if (!state) return null;

  // Convert the native physical layout into this webview's measured CSS size.
  const scaleX =
    (viewport.width * state.metadata.scaleFactor) / state.layout.windowWidth;
  const scaleY =
    (viewport.height * state.metadata.scaleFactor) / state.layout.windowHeight;
  const contentWidth = state.layout.contentWidth * scaleX;
  const contentHeight = state.layout.contentHeight * scaleY;
  const selectedRegionId = activeRegionId;
  const activeRegionIndex = Math.max(
    0,
    state.regions.findIndex((region) => region.id === activeRegionId),
  );
  const selectedRegion = state.regions.find(
    (region) => region.id === activeRegionId,
  );
  const controlsTop = Math.max(
    0,
    Math.min(viewport.height - 28, state.layout.toolbarTop * scaleY + 2),
  );
  const textBounds = new Map(
    state.regions.map((region) => {
      const points = ocrPolygonToOverlay(region.polygon, state.metadata, {
        width: contentWidth,
        height: contentHeight,
      });
      const x = Math.max(0, Math.min(...points.map((point) => point.x)));
      const y = Math.max(0, Math.min(...points.map((point) => point.y)));
      const right = Math.min(
        contentWidth,
        Math.max(...points.map((point) => point.x)),
      );
      const bottom = Math.min(
        contentHeight,
        Math.max(...points.map((point) => point.y)),
      );
      return [
        region.id,
        {
          x,
          y,
          width: Math.max(0, right - x),
          height: Math.max(0, bottom - y),
        },
      ];
    }),
  );
  const neighbours = [...textBounds.values()];

  const handleRegionClick = async (region: TextRegion, keyboard = false) => {
    setActiveRegionId(region.id);
    setPopupError(null);
    try {
      await invoke("show_translation_popup", {
        metadata: state.metadata,
        text: region.text,
        polygon: region.polygon,
        regionId: region.id,
        ...(state.sessionId !== undefined
          ? { sessionId: state.sessionId }
          : {}),
        keyboard,
        ...(translationEnabled && translations.has(region.id)
          ? { translateOnOpen: true }
          : {}),
      });
    } catch (error) {
      setPopupError(String(error));
    }
  };

  return (
    <div
      className="ocr-overlay"
      ref={navigatorRef}
      tabIndex={-1}
      role="group"
      aria-label="OCR region navigator"
      aria-describedby="region-navigation-help"
      onKeyDown={(event) => {
        if (event.defaultPrevented || event.target !== event.currentTarget)
          return;
        const index = activeRegionIndex;
        if (
          [
            "ArrowUp",
            "ArrowDown",
            "ArrowLeft",
            "ArrowRight",
            "Home",
            "End",
          ].includes(event.key)
        ) {
          event.preventDefault();
          navigateRegion(event.key, index);
        } else if (
          (event.key === "Enter" || event.key === " ") &&
          state.regions[index]
        ) {
          event.preventDefault();
          void handleRegionClick(state.regions[index], true);
        }
      }}
    >
      <p className="visually-hidden" id="region-navigation-help">
        Use arrow keys to move between text regions, Enter or Space to open, and
        Escape to hide OCR overlays. Navigation follows detected regions;
        whole-screen order is estimated and may differ from manga panel order.
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
        {state.regions.map((region) => {
          const translation = translationEnabled && translations.get(region.id);
          if (!translation) return null;
          const bounds = textBounds.get(region.id)!;
          const availableBounds = availableTranslationBounds(
            bounds,
            neighbours,
            contentWidth,
            contentHeight,
          );
          if (bounds.width <= 0 || bounds.height <= 0) return null;
          return (
            <Fragment key={region.id}>
              <BubbleTranslation
                text={translation}
                bounds={bounds}
                availableBounds={availableBounds}
                needsReview={Boolean(
                  region.needsReview || region.geometrySource,
                )}
                selected={selectedRegionId === region.id}
                onActivate={() => void handleRegionClick(region)}
                elementRef={(element) => {
                  if (element)
                    translationElements.current.set(region.id, element);
                  else translationElements.current.delete(region.id);
                }}
              />
            </Fragment>
          );
        })}
        {state.regions.map((region, index) => (
          <OCRBoundingBox
            region={region}
            demo={state.engine === "demo"}
            translation={
              translationEnabled ? translations.get(region.id) : undefined
            }
            selected={selectedRegionId === region.id}
            tabIndex={index === activeRegionIndex ? 0 : -1}
            elementRef={(element) => {
              if (element) regionElements.current.set(region.id, element);
              else regionElements.current.delete(region.id);
            }}
            onFocus={() => setActiveRegionId(region.id)}
            onActivate={(keyboard) => void handleRegionClick(region, keyboard)}
            onNavigate={(key) => navigateRegion(key, index)}
            key={region.id}
            points={polygonPoints(region, state.metadata, {
              width: contentWidth,
              height: contentHeight,
            })}
          />
        ))}
      </svg>
      {state.sessionId !== undefined && revealed && translatable.length > 0 && (
        <div
          ref={translationControls}
          className="overlay-translation-controls"
          style={
            controlsTop > viewport.height / 2
              ? { bottom: viewport.height - controlsTop - 28 }
              : { top: controlsTop }
          }
        >
          <button
            type="button"
            className="overlay-translation-toggle"
            aria-pressed={translationEnabled}
            title={
              translationEnabled
                ? "Show original Japanese"
                : "Translate detected text with the selected local model"
            }
            onClick={() => setTranslationEnabled((enabled) => !enabled)}
          >
            Translate bubbles
          </button>
          {translationEnabled && (
            <>
              <span
                className="overlay-translation-status"
                role={translationError ? "alert" : "status"}
              >
                {translationError ??
                  (pending
                    ? `Translating locally ${translations.size}/${translatable.length}…`
                    : "Machine translation · Click a region for details")}
              </span>
              {translationError && (
                <button
                  type="button"
                  onClick={() =>
                    setTranslationAttempt((attempt) => attempt + 1)
                  }
                >
                  Retry
                </button>
              )}
            </>
          )}
        </div>
      )}
      {state.sessionId !== undefined && revealed && (
        <button
          ref={hideButton}
          className="overlay-hide"
          aria-label="Hide OCR overlays"
          aria-keyshortcuts="Escape"
          title="Hide OCR overlays (Esc)"
          disabled={hiding}
          style={{
            top: controlsTop,
          }}
          onClick={() => {
            if (hidePending.current) return;
            hidePending.current = true;
            setTranslationEnabled(false);
            setHiding(true);
            setPopupError(null);
            void invoke("hide_completed_ocr_overlay", {
              sessionId: state.sessionId,
            })
              .catch((error) =>
                setPopupError(`Could not hide OCR overlays: ${String(error)}`),
              )
              .finally(() => {
                hidePending.current = false;
                setHiding(false);
              });
          }}
        >
          <ToolbarIcon name="close" />
        </button>
      )}
    </div>
  );
}
