import type { Rectangle } from "../../lib/coordinates";

/** Maximum space a panel may use; actual text fitting chooses how much it needs. */
export function availableTranslationBounds(
  source: Rectangle,
  neighbours: Rectangle[],
  contentWidth: number,
  contentHeight: number,
): Rectangle {
  let left = 0,
    right = contentWidth,
    top = 0,
    bottom = contentHeight;
  for (const other of neighbours) {
    if (other === source) continue;
    const horizontalGap = Math.max(
      other.x - source.x - source.width,
      source.x - other.x - other.width,
    );
    const verticalGap = Math.max(
      other.y - source.y - source.height,
      source.y - other.y - other.height,
    );
    // Each pair uses the same separating axis, including diagonal neighbours.
    // Sharing that gap prevents independently growing panels from colliding.
    if (horizontalGap < 0 && verticalGap < 0) return source;
    if (horizontalGap >= verticalGap) {
      if (other.x >= source.x + source.width)
        right = Math.min(right, (source.x + source.width + other.x) / 2 - 2);
      else left = Math.max(left, (other.x + other.width + source.x) / 2 + 2);
    } else {
      if (other.y >= source.y + source.height)
        bottom = Math.min(bottom, (source.y + source.height + other.y) / 2 - 2);
      else top = Math.max(top, (other.y + other.height + source.y) / 2 + 2);
    }
  }
  // Never crop the original rectangle, even when OCR regions touch.
  left = Math.min(left, source.x);
  right = Math.max(right, source.x + source.width);
  top = Math.min(top, source.y);
  bottom = Math.max(bottom, source.y + source.height);
  const width = Math.min(Math.max(source.width, 240), right - left);
  const height = Math.min(Math.max(source.height, 220), bottom - top);
  return anchorTranslationBounds(
    source,
    { x: left, y: top, width: right - left, height: bottom - top },
    width,
    height,
  );
}

/** Keep a fitted rectangle anchored over its source, inside its available space. */
export function anchorTranslationBounds(
  source: Rectangle,
  available: Rectangle,
  width: number,
  height: number,
): Rectangle {
  return {
    x: Math.max(
      available.x,
      Math.min(
        source.x + (source.width - width) / 2,
        available.x + available.width - width,
      ),
    ),
    y: Math.max(
      available.y,
      Math.min(
        source.y + (source.height - height) / 2,
        available.y + available.height - height,
      ),
    ),
    width,
    height,
  };
}
