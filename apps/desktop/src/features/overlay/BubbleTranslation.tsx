import { useLayoutEffect, useRef, useState } from "react";
import type { Rectangle } from "../../lib/coordinates";

/** Region polygons retain keyboard navigation; this surface also accepts scrolling. */
export function BubbleTranslation({
  text,
  bounds,
  elementRef,
  onActivate,
  needsReview = false,
  selected = false,
}: {
  text: string;
  bounds: Rectangle;
  elementRef: (element: HTMLDivElement | null) => void;
  onActivate: () => void;
  needsReview?: boolean;
  selected?: boolean;
}) {
  const content = useRef<HTMLSpanElement>(null);
  const [overflowing, setOverflowing] = useState(false);

  useLayoutEffect(() => {
    const span = content.current;
    if (!span) return;
    const fit = () => {
      const parent = span.parentElement!;
      // Measure with the scrollbar gutter reserved, so overflow cannot create
      // another wrapping change after fitting. Keep the full text in the DOM.
      const width = parent.clientWidth - 8;
      const height = parent.clientHeight - 8;
      let size = 18;
      span.style.fontSize = `${size}px`;
      while (
        size > 11 &&
        (span.scrollHeight > height || span.scrollWidth > width)
      ) {
        span.style.fontSize = `${--size}px`;
      }
      setOverflowing(span.scrollHeight > height || span.scrollWidth > width);
      parent.scrollTop = 0;
    };
    fit();
    const observer =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(fit);
    observer?.observe(span.parentElement!);
    return () => observer?.disconnect();
  }, [text, bounds.width, bounds.height]);

  return (
    <foreignObject
      {...bounds}
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
