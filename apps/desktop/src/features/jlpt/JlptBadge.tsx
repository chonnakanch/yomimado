import { jlptLevel } from "./jlpt";
import "./jlpt.css";

export function JlptBadge({
  expression,
  reading,
}: {
  expression: string;
  reading: string;
}) {
  const level = jlptLevel(expression, reading);
  return level ? (
    <span
      className="jlpt-badge"
      lang="en"
      aria-label={`Estimated JLPT level ${level}`}
      title={`Estimated JLPT ${level} · Jonathan Waller / Stephen Kraus · CC BY-SA 4.0. See Sources & licenses.`}
    >
      {level}
    </span>
  ) : null;
}
