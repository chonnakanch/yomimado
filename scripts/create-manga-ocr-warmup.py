"""Replace Manga OCR's example artwork with a generated warm-up image."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


def main() -> None:
    destination = Path(sys.argv[1])
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), "white").save(destination, format="JPEG", quality=90)


if __name__ == "__main__":
    main()
