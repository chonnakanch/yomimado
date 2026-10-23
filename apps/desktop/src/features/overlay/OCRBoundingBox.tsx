import type { TextRegion } from "../../lib/ocr-types";
import { captureDebugEnabled } from "../../lib/debug-mode";

export function regionLabel(
  region: TextRegion,
  demo: boolean,
  number?: number,
) {
  return `${number ? `${number}. ` : ""}${demo ? "Demo boundary — no recognized text" : region.text} (${region.orientation}${region.geometrySource ? ", Approximate region" : ""}${region.needsReview ? ", Review OCR" : ""})${region.reviewReason ? ` — ${region.reviewReason}` : ""}`;
}

export function OCRBoundingBox({
  region,
  points,
  selected,
  demo,
  tabIndex,
  number,
  onActivate,
  onFocus,
  onNavigate,
  elementRef,
  translation,
}: {
  region: TextRegion;
  points: string;
  selected: boolean;
  demo: boolean;
  tabIndex: number;
  number?: number;
  onActivate: (keyboard: boolean) => void;
  onFocus: () => void;
  onNavigate: (key: string) => void;
  elementRef: (element: SVGPolygonElement | null) => void;
  translation?: string;
}) {
  const originalLabel = regionLabel(region, demo, number);
  const label = translation
    ? `Machine translation: ${translation}. Japanese: ${originalLabel}`
    : originalLabel;
  const stateClasses = `${demo ? " demo" : ""}${region.geometrySource ? " approximate" : ""}${region.needsReview ? " needs-review" : ""}${selected ? " active" : ""}`;
  return (
    <polygon
      className={`ocr-region${stateClasses}${translation ? " translated" : ""}`}
      points={points}
      role="button"
      aria-label={label}
      aria-pressed={selected}
      tabIndex={tabIndex}
      ref={elementRef}
      onFocus={onFocus}
      onClick={(event) => onActivate(event.detail === 0)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onActivate(true);
        } else if (
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
          onNavigate(event.key);
        }
      }}
    >
      {(captureDebugEnabled() || translation) && (
        <title>
          {translation
            ? `${label}. Click to read in the learning popup.`
            : label}
        </title>
      )}
    </polygon>
  );
}
