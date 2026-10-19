import { useEffect, useId, useLayoutEffect, useRef } from "react";
import type { TextToken } from "../../lib/ocr-types";

// Textareas use UTF-16 offsets and normalize line endings; OCR uses code points
// in the original source. Keep both conversions here, without changing the text.
export function selectionToken(
  source: string,
  start: number,
  end: number,
): TextToken | null {
  const displayed = source.replace(/\r\n?/g, "\n");
  if (
    !Number.isInteger(start) ||
    !Number.isInteger(end) ||
    start < 0 ||
    end > displayed.length ||
    start >= end
  )
    return null;
  const selected = displayed.slice(start, end);
  start += selected.length - selected.trimStart().length;
  end -= selected.length - selected.trimEnd().length;
  if (start >= end) return null;
  const splitsCharacter = (offset: number) =>
    /[\uD800-\uDBFF]/.test(displayed.charAt(offset - 1)) &&
    /[\uDC00-\uDFFF]/.test(displayed.charAt(offset));
  if (splitsCharacter(start) || splitsCharacter(end)) return null;
  const sourceOffset = (offset: number) => {
    let original = 0;
    for (let index = 0; index < offset; index++) {
      original +=
        source[original] === "\r" && source[original + 1] === "\n" ? 2 : 1;
    }
    return original;
  };
  const originalStart = sourceOffset(start);
  const originalEnd = sourceOffset(end);
  const surface = source.slice(originalStart, originalEnd);
  return {
    surface,
    dictionaryForm: surface,
    reading: "",
    partOfSpeech: "",
    start: Array.from(source.slice(0, originalStart)).length,
    end: Array.from(source.slice(0, originalEnd)).length,
  };
}

export function ManualWordSelection({
  source,
  maxHeight,
  onSelectionChange,
}: {
  source: string;
  maxHeight: number;
  onSelectionChange: (token: TextToken | null) => void;
}) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const helpId = useId();
  useLayoutEffect(() => {
    const input = inputRef.current;
    if (!input) return;
    let lastWidth = -1;
    const fitText = () => {
      if (input.clientWidth === lastWidth) return;
      lastWidth = input.clientWidth;
      const style = getComputedStyle(input);
      const borders =
        (parseFloat(style.borderTopWidth) || 0) +
        (parseFloat(style.borderBottomWidth) || 0);
      input.style.height = "0px";
      input.style.height = `${input.scrollHeight + borders}px`;
    };
    fitText();
    const observer =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(fitText);
    observer?.observe(input);
    return () => observer?.disconnect();
  }, [source, maxHeight]);
  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.setSelectionRange(0, 0);
  }, []);
  return (
    <>
      <p className="visually-hidden" id={helpId}>
        Drag to select text, or hold Shift and use the arrow keys.
      </p>
      <textarea
        ref={inputRef}
        className="sentence-selection-text"
        aria-label="Select Japanese text for lookup"
        aria-describedby={helpId}
        lang="ja"
        readOnly
        value={source}
        rows={1}
        style={{ maxHeight }}
        onSelect={(event) => {
          onSelectionChange(
            selectionToken(
              source,
              event.currentTarget.selectionStart,
              event.currentTarget.selectionEnd,
            ),
          );
        }}
      />
    </>
  );
}
