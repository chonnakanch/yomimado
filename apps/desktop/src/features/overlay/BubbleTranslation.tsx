import { useLayoutEffect, useRef, useState } from "react";
import type { Rectangle } from "../../lib/coordinates";

/** Visual only; the existing region navigator continues to own activation. */
export function BubbleTranslation({
  text,
  bounds,
  elementRef,
}: {
  text: string;
  bounds: Rectangle;
  elementRef: (element: HTMLDivElement | null) => void;
}) {
  const content = useRef<HTMLSpanElement>(null);
  const [overflowing, setOverflowing] = useState(false);

  useLayoutEffect(() => {
    const span = content.current;
    if (!span) return;
    const fit = () => {
      const parent = span.parentElement!;
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
        className={`bubble-translation-text${overflowing ? " is-overflowing" : ""}`}
        title={`Machine translation: ${text}${overflowing ? " — Click to read in the learning popup." : ""}`}
        lang="en"
      >
        <span ref={content}>{text}</span>
      </div>
    </foreignObject>
  );
}
