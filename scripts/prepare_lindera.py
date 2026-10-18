"""Stage the pinned IPADIC resource; downloads happen only in explicit preparation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "services/ocr"
sys.path.insert(0, str(SERVICE))
from app.tokenizer.lindera import INPUTS, verify_dictionary


def digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stage(archive: Path, destination: Path, pins: dict) -> None:
    expected = pins["dictionary"]["files"]
    if digest(archive) != pins["dictionary"]["sha256"]:
        raise ValueError("Lindera dictionary archive checksum differs")
    if destination.exists():
        verify_dictionary(destination, expected)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    prefix = "lindera-ipadic/"
    with zipfile.ZipFile(archive) as bundle:
        members = [item for item in bundle.infolist() if not item.is_dir()]
        names = [item.filename for item in members]
        if len(names) != len(set(names)) or set(names) != {
            prefix + name for name in expected
        }:
            raise ValueError("Unexpected Lindera dictionary archive membership")
        if any((item.external_attr >> 16) & 0o170000 == 0o120000 for item in members):
            raise ValueError("Lindera dictionary archive contains a symbolic link")
        with tempfile.TemporaryDirectory(
            prefix=".lindera-stage-", dir=destination.parent
        ) as temporary:
            temporary = Path(temporary)
            for item in members:
                with (
                    bundle.open(item) as source,
                    (temporary / Path(item.filename).name).open("wb") as target,
                ):
                    shutil.copyfileobj(source, target)
            verify_dictionary(temporary, expected)
            temporary.rename(destination)


def retain_notices(destination: Path, pins: dict) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name, sha in pins["noticeHashes"].items():
        source = ROOT / "THIRD_PARTY_LICENSES/lindera" / name
        if digest(source) != sha:
            raise ValueError("Lindera notice checksum differs: " + name)
        shutil.copyfile(source, destination / name)
    shutil.copyfile(INPUTS, destination / "lindera-inputs.json")
    shutil.copyfile(
        ROOT / "THIRD_PARTY_LICENSES/lindera/README.md", destination / "README.md"
    )


def verify_packaged(resources: Path) -> None:
    """Reject missing/changed dictionary inputs and accidentally retained Sudachi."""
    pins = json.loads(INPUTS.read_text())
    verify_dictionary(resources / "assets/lindera-ipadic", pins["dictionary"]["files"])
    notices = resources / "notices/lindera"
    if digest(notices / "lindera-inputs.json") != digest(INPUTS):
        raise ValueError("Packaged Lindera input manifest differs")
    for name, sha in pins["noticeHashes"].items():
        if digest(notices / name) != sha:
            raise ValueError("Packaged Lindera notice differs: " + name)
    internal = resources / "runtime/_internal"
    for entry in internal.iterdir():
        if (
            entry.name.lower()
            .replace("-", "_")
            .startswith(("sudachipy", "sudachidict_core"))
        ):
            raise ValueError("Replaced Sudachi resources remain in the frozen service")
    if digest(internal / "app/tokenizer/lindera-inputs.json") != digest(INPUTS):
        raise ValueError("Frozen Lindera runtime pins differ")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target", type=Path, default=SERVICE / "local-dictionaries/lindera-ipadic"
    )
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--notices", type=Path)
    args = parser.parse_args()
    pins = json.loads(INPUTS.read_text())
    if args.check:
        verify_dictionary(args.target, pins["dictionary"]["files"])
    else:
        archive = (
            args.archive
            or SERVICE / "build/lindera-inputs" / pins["dictionary"]["filename"]
        )
        if not archive.is_file():
            if not args.download:
                parser.error(
                    "Supply --archive or use --download during resource preparation"
                )
            archive.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=archive.parent) as temporary:
                downloaded = Path(temporary) / archive.name
                with (
                    urllib.request.urlopen(
                        pins["dictionary"]["url"], timeout=60
                    ) as response,
                    downloaded.open("wb") as target,
                ):
                    shutil.copyfileobj(response, target)
                if digest(downloaded) != pins["dictionary"]["sha256"]:
                    raise ValueError("Downloaded Lindera archive checksum differs")
                downloaded.replace(archive)
        stage(archive, args.target, pins)
    if args.notices:
        retain_notices(args.notices, pins)
    print("Verified Lindera 6.0.0/IPADIC: " + str(args.target))


if __name__ == "__main__":
    main()
