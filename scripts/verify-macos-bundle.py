"""Check the contents of a private/release macOS .app before distribution."""

from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import sys
from pathlib import Path

from opencv_release import VIDEO_LIBRARY, verify_record
from PIL import Image

MACHO = {
    b"\xfe\xed\xfa\xce",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf",
    b"\xbf\xba\xfe\xca",
}

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
    "macos-source-review.md",
    "native-libraries.json",
    "project-revision.txt",
    "opencv-build.json",
    "python-build.json",
    "opencv-source-changes.diff",
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


def verify_python_provenance(record: dict, binaries: list[dict], notices: Path) -> None:
    if (
        record.get("pythonVersion") != "3.11.17"
        or record.get("opensslVersion") != "3.5.9"
        or record.get("lzmaVersion") != "5.8.4"
    ):
        raise ValueError("Bundled Python/OpenSSL versions differ from source build")
    if set(record["noticeHashes"]) != {
        "CPython-LICENSE.txt",
        "OpenSSL-LICENSE.txt",
        "Expat-COPYING.txt",
        "libmpdec-COPYRIGHT.txt",
        "SHA3-LICENSE.txt",
        "Mersenne-Twister-NOTICE.txt",
        "BLAKE2-NOTICE.txt",
        "dtoa-NOTICE.txt",
        "SipHash-NOTICE.txt",
        "liblzma-LICENSE.txt",
        "XZ-COPYING.txt",
    }:
        raise ValueError("Bundled runtime notice coverage is incomplete")
    inputs = {
        "interpreter/" + Path(name).name: digest
        for name, digest in record["binaries"].items()
    }
    frozen = [
        item for item in binaries if item["buildInput"].startswith("interpreter/")
    ]
    if not frozen or not any(
        item["buildInput"] == "interpreter/libpython3.11.dylib" for item in frozen
    ):
        raise ValueError("Missing source-built Python input provenance")
    for item in frozen:
        if inputs.get(item["buildInput"]) != item["buildInputSha256"]:
            raise ValueError(
                "Frozen Python input differs from its source build: "
                + item["buildInput"]
            )
    for name, expected in record["noticeHashes"].items():
        component = "CPython-3.11.17"
        if name == "OpenSSL-LICENSE.txt":
            component = "OpenSSL-3.5.9"
        elif name in {"liblzma-LICENSE.txt", "XZ-COPYING.txt"}:
            component = "liblzma-5.8.4"
        base = notices / "licenses/source" / component
        path = (base / name).resolve()
        if (
            not path.is_relative_to(base.resolve())
            or not path.is_file()
            or sha256_file(path) != expected
        ):
            raise ValueError(
                "Bundled runtime notice differs from source build: " + name
            )


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
    components = []
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
    native = notices / "native-libraries.json"
    if native.is_file():
        binaries = json.loads(native.read_text())["binaries"]
        python_record = notices / "python-build.json"
        if python_record.is_file():
            try:
                verify_python_provenance(
                    json.loads(python_record.read_text()), binaries, notices
                )
            except (ValueError, KeyError) as error:
                errors.append(str(error))
        opencv_record = notices / "opencv-build.json"
        if opencv_record.is_file():
            try:
                record = json.loads(opencv_record.read_text())
                verify_record(record)
                opencv_notices = [
                    notices / relative
                    for component in components
                    if component["name"] == "opencv-python"
                    for relative in component["noticeFiles"]
                    if Path(relative).name == "LICENSE-3RD-PARTY.txt"
                ]
                if not opencv_notices or any(
                    not path.is_file()
                    or sha256_file(path)
                    != record["modifiedFiles"]["LICENSE-3RD-PARTY.txt"]
                    for path in opencv_notices
                ):
                    errors.append(
                        "Bundled OpenCV static notices do not match source build"
                    )
                opencv_inputs = [
                    item
                    for item in binaries
                    if item["buildInput"].startswith("site-packages/cv2/")
                    and item["path"].endswith(".so")
                ]
                if not opencv_inputs or any(
                    item["buildInputSha256"] != record["binarySha256"]
                    for item in opencv_inputs
                ):
                    errors.append(
                        "Frozen OpenCV input does not match source build provenance"
                    )
            except (ValueError, KeyError) as error:
                errors.append(str(error))
        if not binaries:
            errors.append("Empty native binary inventory")
        for binary in binaries:
            path = (resources / "runtime/_internal" / binary["path"]).resolve()
            if not path.is_relative_to(resources.resolve()) or not path.is_file():
                errors.append(f"Missing/unsafe native runtime path: {binary['path']}")
        listed = {binary["path"] for binary in binaries}
        internal = resources / "runtime/_internal"
        for path in internal.rglob("*"):
            if VIDEO_LIBRARY.match(path.name):
                errors.append(
                    f"Prohibited video dependency: {path.relative_to(internal)}"
                )
            if not path.is_file() or path.is_symlink():
                continue
            with path.open("rb") as stream:
                if (
                    stream.read(4) in MACHO
                    and str(path.relative_to(internal)) not in listed
                ):
                    errors.append(
                        f"Unlisted native runtime binary: {path.relative_to(internal)}"
                    )
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
