"""Fail the macOS release build if its Python environment has drifted."""

from __future__ import annotations

import importlib.metadata
import re
import sys
from pathlib import Path

LOCK = (
    Path(__file__).resolve().parents[1] / "services/ocr/requirements-macos-release.txt"
)
PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s]+)$")


def main() -> int:
    errors = []
    if sys.version_info[:2] != (3, 9):
        errors.append("The macOS release build requires Python 3.9.")
    for line in LOCK.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = PIN.fullmatch(line)
        if not match:
            errors.append(f"Invalid release pin: {line}")
            continue
        name, expected = match.groups()
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            errors.append(f"Missing {name}=={expected}")
            continue
        if actual != expected:
            errors.append(f"{name}: expected {expected}, installed {actual}")
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print("Python release environment matches version pins.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
