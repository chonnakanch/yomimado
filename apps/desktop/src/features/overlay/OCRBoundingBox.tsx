import type { TextRegion } from "../../lib/ocr-types";

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
}) {
  const label = regionLabel(region, demo, number);
  return (
    <polygon
      className={`ocr-region${demo ? " demo" : ""}${region.geometrySource ? " approximate" : ""}${region.needsReview ? " needs-review" : ""}${selected ? " active" : ""}`}
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
      <title>{label}</title>
    </polygon>
  );
}
