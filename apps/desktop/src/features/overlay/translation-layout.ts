import type { Rectangle } from "../../lib/coordinates";

/** Give narrow English text some room without crossing neighboring text regions. */
export function widenTranslationBounds(
  source: Rectangle,
  neighbours: Rectangle[],
  contentWidth: number,
): Rectangle {
  let left = 0;
  let right = contentWidth;
  const sourceRight = source.x + source.width;
  for (const other of neighbours) {
    if (other === source) continue;
    if (
      other.y + other.height <= source.y ||
      other.y >= source.y + source.height
    )
      continue;
    const otherRight = other.x + other.width;
    if (otherRight <= source.x) {
      left = Math.max(left, (otherRight + source.x) / 2 + 2);
    } else if (other.x >= sourceRight) {
      right = Math.min(right, (sourceRight + other.x) / 2 - 2);
    } else {
      // Existing overlapping OCR remains unchanged; do not enlarge its coverage.
      return source;
    }
  }
  left = Math.min(left, source.x);
  right = Math.max(right, sourceRight);
  const width = Math.min(
    Math.max(source.width, Math.min(140, source.width * 1.6)),
    right - left,
  );
  const x = Math.max(
    left,
    Math.min(source.x + (source.width - width) / 2, right - width),
  );
  return { ...source, x, width };
}
