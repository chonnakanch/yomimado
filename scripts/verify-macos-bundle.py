"""Check the contents of a private/release macOS .app before distribution."""

from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import sys
from pathlib import Path

from PIL import Image

EXPECTED_ASSETS = (
    "manga-ocr-base/pytorch_model.bin",
    "opus-mt-ja-en/pytorch_model.bin",
    "JMdict_e.gz",
    "kanjidic2.xml.gz",
)
REQUIRED_NOTICES = (
    "LICENSE",
    "MODEL_CREDITS.md",
    "ASSET_NOTICES.md",
    "THIRD_PARTY_SOFTWARE.md",
    "third-party-manifest.json",
    "upstream-notice-sources.json",
    "asset-checksums.txt",
    "dictionary-updates.md",
    "assets/Apache-2.0.txt",
    "assets/CC-BY-SA-4.0.txt",
    "assets/EDRDG-dictionary-licence.html",
    "assets/manga-ocr-model-card.md",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(app: Path) -> list[str]:
    errors = []
    resources = app / "Contents/Resources/ocr"
    assets = resources / "assets"
    notices = resources / "notices"
    info = app / "Contents/Info.plist"
    if not info.is_file():
        return [f"Missing macOS app metadata: {info}"]
    with info.open("rb") as stream:
        bundle = plistlib.load(stream)
    if bundle.get("CFBundleIdentifier") != "com.yomimado.desktop":
        errors.append("Unexpected bundle identifier")
    if not (resources / "runtime/yomimado-ocr").is_file():
        errors.append("Missing packaged OCR service")
    warmup = resources / "runtime/_internal/manga_ocr/assets/example.jpg"
    if not warmup.is_file():
        errors.append("Missing generated Manga OCR warm-up image")
    else:
        with Image.open(warmup) as image:
            if image.size != (64, 64) or image.convert("RGB").getextrema() != (
                (255, 255),
                (255, 255),
                (255, 255),
            ):
                errors.append("Manga OCR warm-up image is not the generated blank")
    if not (assets / "comic-text-detector/LICENSE").is_file():
        errors.append("Missing detector source licence")

    for name in EXPECTED_ASSETS:
        if not (assets / name).is_file():
            errors.append(f"Missing asset: {name}")
    for name in REQUIRED_NOTICES:
        if not (notices / name).is_file():
            errors.append(f"Missing notice: {name}")

    prohibited = [
        path.relative_to(app)
        for path in app.rglob("*")
        if path.is_file()
        and path != warmup
        and path.suffix.lower() in {".onnx", ".jpg", ".jpeg", ".png", ".ttc"}
    ]
    if prohibited:
        errors.append(
            "Unexpected model/sample files: " + ", ".join(map(str, prohibited))
        )

    checksums = notices / "asset-checksums.txt"
    if checksums.is_file():
        entries = {}
        for line in checksums.read_text().splitlines():
            digest, name = line.split(None, 1)
            entries[name.strip()] = digest
        if set(entries) != set(EXPECTED_ASSETS):
            errors.append("Asset checksum inventory does not match expected assets")
        for name, expected in entries.items():
            path = assets / name
            if path.is_file() and sha256_file(path) != expected:
                errors.append(f"Asset checksum mismatch: {name}")

    manifest = notices / "third-party-manifest.json"
    if manifest.is_file():
        components = json.loads(manifest.read_text())["components"]
        if not components:
            errors.append("Empty third-party software manifest")
        for item in components:
            license_summary = item["license"]
            if (
                license_summary == "UNKNOWN"
                or "\n" in license_summary
                or len(license_summary) > 120
                or not item["noticeFiles"]
            ):
                errors.append(f"Missing licence for {item['ecosystem']} {item['name']}")
            for relative in item["noticeFiles"]:
                if not (notices / relative).is_file():
                    errors.append(f"Missing component notice: {relative}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path)
    args = parser.parse_args()
    errors = verify(args.app.resolve())
    for error in errors:
        print(f"FAIL: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"Verified bundle contents: {args.app}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
