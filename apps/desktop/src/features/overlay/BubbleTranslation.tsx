import { useLayoutEffect, useRef, useState } from "react";
import type { Rectangle } from "../../lib/coordinates";
import { anchorTranslationBounds } from "./translation-layout";

/** Region polygons retain keyboard navigation; this surface also accepts scrolling. */
export function BubbleTranslation({
  text,
  bounds,
  availableBounds = bounds,
  elementRef,
  onActivate,
  needsReview = false,
  selected = false,
}: {
  text: string;
  bounds: Rectangle;
  availableBounds?: Rectangle;
  elementRef: (element: HTMLDivElement | null) => void;
  onActivate: () => void;
  needsReview?: boolean;
  selected?: boolean;
}) {
  const content = useRef<HTMLSpanElement>(null);
  const [overflowing, setOverflowing] = useState(false);
  const [fittedBounds, setFittedBounds] = useState(bounds);

  useLayoutEffect(() => {
    const span = content.current;
    if (!span) return;
    const parent = span.parentElement!;
    let width = bounds.width;
    let height = bounds.height;
    let overflow = false;
    // Use space at 18px before reducing the font. Measure real wrapping with
    // the scrollbar gutter reserved, and retain every word when space runs out.
    for (let size = 18; size >= 11; size--) {
      span.style.fontSize = `${size}px`;
      width = bounds.width;
      while (true) {
        parent.style.width = `${width}px`;
        if (
          (span.scrollHeight <= bounds.height - 12 &&
            span.scrollWidth <= parent.clientWidth - 8) ||
          width >= availableBounds.width
        )
          break;
        width = Math.min(availableBounds.width, width + 12);
      }
      height = Math.min(
        availableBounds.height,
        Math.max(bounds.height, span.scrollHeight + 12),
      );
      overflow =
        span.scrollHeight > height - 12 ||
        span.scrollWidth > parent.clientWidth - 8;
      if (!overflow) break;
    }
    parent.style.width = "100%";
    setFittedBounds(
      anchorTranslationBounds(bounds, availableBounds, width, height),
    );
    setOverflowing(overflow);
    parent.scrollTop = 0;
  }, [
    text,
    bounds.x,
    bounds.y,
    bounds.width,
    bounds.height,
    availableBounds.x,
    availableBounds.y,
    availableBounds.width,
    availableBounds.height,
  ]);

  return (
    <foreignObject
      {...fittedBounds}
      aria-hidden="true"
      className="bubble-translation"
    >
      <div
        ref={elementRef}
        className={`bubble-translation-text${overflowing ? " is-overflowing" : ""}${needsReview ? " needs-review" : ""}${selected ? " active" : ""}`}
        title={`Machine translation: ${text}${overflowing ? " — Scroll to read more, or click to open the learning popup." : ""}`}
        lang="en"
        onClick={onActivate}
      >
        <span ref={content}>{text}</span>
      </div>
    </foreignObject>
  );
}
