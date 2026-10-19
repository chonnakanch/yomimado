import { useEffect, useId, useRef, useState } from "react";
import type { TextToken } from "../../lib/ocr-types";
import { isWord } from "./ClickableSentence";

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
  onLookup,
}: {
  source: string;
  maxHeight: number;
  onLookup: (token: TextToken) => void;
}) {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const helpId = useId();
  const [range, setRange] = useState({
    start: 0,
    end: 0,
    direction: "none" as "forward" | "backward" | "none",
  });
  const token = selectionToken(source, range.start, range.end);
  // Matches the existing local word API limit, measured in Unicode code points.
  const tooLong = !!token && token.end - token.start > 100;
  useEffect(() => {
    const input = inputRef.current;
    if (!input) return;
    // Native readOnly hides the caret in WebKit. Keep native text navigation,
    // but cancel edits before they change this selection-only copy of the source.
    const preventEdit = (event: InputEvent) => event.preventDefault();
    input.addEventListener("beforeinput", preventEdit);
    input.focus();
    input.setSelectionRange(0, 0);
    return () => input.removeEventListener("beforeinput", preventEdit);
  }, []);
  return (
    <>
      <p className="popup-metadata" id={helpId}>
        Drag to select text, or click to place the cursor. Arrow keys move it;
        Shift + arrow keys select text.
      </p>
      <textarea
        ref={inputRef}
        className="sentence-selection-text"
        aria-label="Select Japanese text for lookup"
        aria-describedby={helpId}
        lang="ja"
        aria-readonly="true"
        spellCheck={false}
        value={source}
        rows={3}
        style={{ maxHeight }}
        onPaste={(event) => event.preventDefault()}
        onCut={(event) => event.preventDefault()}
        onDrop={(event) => event.preventDefault()}
        onChange={(event) => {
          // Also restore the source for non-cancelable input (for example IME).
          const input = event.currentTarget;
          input.value = source.replace(/\r\n?/g, "\n");
          input.setSelectionRange(range.start, range.end, range.direction);
        }}
        onSelect={(event) => {
          setRange({
            start: event.currentTarget.selectionStart,
            end: event.currentTarget.selectionEnd,
            direction: event.currentTarget.selectionDirection,
          });
        }}
      />
      <div className="manual-selection-actions">
        <button
          className="utility-button utility-button-primary"
          disabled={!token || !isWord(token) || tooLong}
          onClick={() => token && onLookup(token)}
        >
          Look up selection
        </button>
        <span className="popup-metadata" role="status">
          {tooLong ? (
            "Select at most 100 characters."
          ) : token ? (
            <span lang="ja">{token.surface}</span>
          ) : (
            "Select the expression to look up."
          )}
        </span>
      </div>
    </>
  );
}
