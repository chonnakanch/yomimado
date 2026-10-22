"""Generate YomiMado's geometric tray marks using only the Python standard library."""

import struct
import zlib
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "apps/desktop/src-tauri/icons"


def rounded(x, y, left, top, right, bottom, radius):
    cx = min(max(x, left + radius), right - radius)
    cy = min(max(y, top + radius), bottom - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius**2


def color_at(x, y, template):
    ink = (0, 0, 0) if template else (16, 20, 27)
    accent = ink if template else (8, 102, 255)
    if rounded(x, y, 14.5, 4, 16, 14.5, 0.75):
        return (*accent, 255)
    if not rounded(x, y, 2, 2, 13.5, 16, 2):
        return (0, 0, 0, 0)
    if not rounded(x, y, 3.5, 3.5, 12, 14.5, 0.75):
        return (*accent, 255)
    if rounded(x, y, 5.5, 5.5, 7, 12.5, 0.75) or rounded(
        x, y, 9, 5.5, 10.5, 10.5, 0.75
    ):
        return (*ink, 255)
    return (0, 0, 0, 0) if template else (244, 247, 255, 255)


def png(size, template):
    # Supersample in the same 18-unit coordinate space for both platform marks.
    samples = 4
    data = bytearray()
    for row in range(size):
        data.append(0)  # PNG filter: None
        for column in range(size):
            colors = [
                color_at(
                    (column + (sx + 0.5) / samples) * 18 / size,
                    (row + (sy + 0.5) / samples) * 18 / size,
                    template,
                )
                for sy in range(samples)
                for sx in range(samples)
            ]
            alpha = sum(color[3] for color in colors)
            for channel in range(3):
                data.append(
                    round(sum(c[channel] * c[3] for c in colors) / alpha)
                    if alpha
                    else 0
                )
            data.append(round(alpha / samples**2))

    def chunk(kind, content):
        return (
            struct.pack(">I", len(content))
            + kind
            + content
            + struct.pack(">I", zlib.crc32(kind + content))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(data, 9))
        + chunk(b"IEND", b"")
    )


if __name__ == "__main__":
    for name, size, template in [
        ("tray-template.png", 36, True),
        ("tray-windows.png", 32, False),
    ]:
        (OUTPUT / name).write_bytes(png(size, template))
