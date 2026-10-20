"""Reproduce the offline JLPT lookup table from retained, hash-pinned data."""

from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "THIRD_PARTY_LICENSES/jlpt"
OUTPUT = ROOT / "apps/desktop/src/features/jlpt/vocabulary.json"


def normalize_reading(text: str) -> str:
    return "".join(
        chr(ord(character) - 0x60) if "ァ" <= character <= "ヶ" else character
        for character in unicodedata.normalize("NFKC", text)
    )


def generate(source: Path, pins: dict) -> bytes:
    levels: dict[str, str] = {}
    for item in pins["files"]:
        path = (source / item["path"]).resolve()
        if not path.is_relative_to(source.resolve()):
            raise ValueError("JLPT input path escapes source directory")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise ValueError(f"JLPT source hash differs: {item['path']}")
        if "level" not in item:
            continue
        expected = item["level"]
        if expected not in ("N1", "N2", "N3", "N4", "N5"):
            raise ValueError("Invalid JLPT source level")
        for expression, kind, metadata in json.loads(content):
            reading = metadata["reading"]
            if (
                kind != "freq"
                or not isinstance(expression, str)
                or not expression
                or not isinstance(reading, str)
                or not reading
                or metadata["frequency"]["displayValue"] != expected
            ):
                raise ValueError("Invalid JLPT source entry")
            key = (
                unicodedata.normalize("NFKC", expression)
                + "\0"
                + normalize_reading(reading)
            )
            if key in levels and levels[key] != expected:
                raise ValueError(
                    "Conflicting JLPT labels for the same spelling/reading"
                )
            levels[key] = expected
    if len(levels) != pins["entryCount"]:
        raise ValueError("JLPT entry count differs")
    result = {
        "source": pins["source"],
        "revision": pins["revision"],
        "license": "CC-BY-SA-4.0",
        "levels": dict(sorted(levels.items())),
    }
    return (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Verify without writing files"
    )
    args = parser.parse_args()
    pins = json.loads((SOURCE / "sources.json").read_text())
    output = generate(SOURCE, pins)
    if hashlib.sha256(output).hexdigest() != pins["outputSha256"]:
        raise ValueError("Generated JLPT dataset hash differs")
    if args.check:
        if OUTPUT.read_bytes() != output:
            raise ValueError("Bundled JLPT dataset differs from pinned source")
        if (OUTPUT.parent / "LICENSE.txt").read_bytes() != (
            SOURCE / "LICENSE.txt"
        ).read_bytes():
            raise ValueError("Bundled JLPT license differs from pinned source")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(output)
        (OUTPUT.parent / "LICENSE.txt").write_bytes(
            (SOURCE / "LICENSE.txt").read_bytes()
        )
    print(f"PASS: {pins['entryCount']} offline JLPT spelling/reading labels verified")


if __name__ == "__main__":
    main()
