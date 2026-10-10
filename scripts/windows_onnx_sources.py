"""Preserve pinned CPU ONNX preferred sources/recipes and original notices.

This source preparation does not approve a prebuilt wheel or public distribution.
No source code is executed. Test weights, media and prebuilt binaries are excluded
from source delivery with a retained content-hash record.
"""

from __future__ import annotations

import base64
import hashlib
import json
import posixpath
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from urllib.request import urlopen

from windows_release import BUILD, RESOURCES, ROOT, digest, fetch, read_json, write_json

MANIFEST = ROOT / "docs/windows-onnx-native-inputs.json"
EXCLUDED = {
    ".onnx",
    ".ort",
    ".pb",
    ".pbtxt",
    ".pt",
    ".pth",
    ".safetensors",
    ".bin",
    ".npy",
    ".npz",
    ".h5",
    ".tflite",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".webp",
    ".mp4",
    ".wav",
    ".exe",
    ".dll",
    ".pyd",
    ".so",
    ".dylib",
    ".a",
    ".lib",
}


def source_tree(original: Path, target: Path) -> list[dict]:
    excluded = []
    # Sorting and then seeking through compressed source archives repeatedly
    # decompresses them. Stage regular files in one streaming pass instead.
    with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
        staged = []
        seen = set()
        total = 0
        with tarfile.open(original, "r|*") as source:
            for member in source:
                path = PurePosixPath(member.name)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in member.name
                    or ":" in member.name
                    or member.name in seen
                    or not (member.isfile() or member.isdir() or member.issym())
                ):
                    raise ValueError("Unsafe preferred-source member")
                seen.add(member.name)
                total += member.size
                if total > 2 * 1024**3:
                    raise ValueError("Preferred-source archive is unexpectedly large")
                if member.issym():
                    linked = posixpath.normpath(
                        posixpath.join(posixpath.dirname(member.name), member.linkname)
                    )
                    if (
                        PurePosixPath(member.linkname).is_absolute()
                        or not linked.startswith(path.parts[0] + "/")
                        or "\\" in member.linkname
                        or ":" in member.linkname
                    ):
                        raise ValueError("Escaping preferred-source symlink")
                if member.isfile() and path.suffix.lower() in EXCLUDED:
                    with source.extractfile(member) as stream:
                        sha = hashlib.file_digest(stream, "sha256").hexdigest()
                    excluded.append(
                        {
                            "path": member.name,
                            "sha256": sha,
                            "reason": "test asset or prebuilt binary; not a runtime source/build input",
                        }
                    )
                    continue
                file = None
                if member.isfile():
                    file = Path(temporary) / str(len(staged))
                    with (
                        source.extractfile(member) as stream,
                        file.open("wb") as output,
                    ):
                        shutil.copyfileobj(stream, output)
                staged.append((member, file))
        with tarfile.open(target, "w", format=tarfile.PAX_FORMAT) as output:
            for member, file in sorted(staged, key=lambda pair: pair[0].name):
                normalized = tarfile.TarInfo(member.name)
                normalized.type = member.type
                normalized.mode = member.mode & 0o777
                normalized.size = member.size if member.isfile() else 0
                normalized.linkname = member.linkname if member.issym() else ""
                if file:
                    with file.open("rb") as stream:
                        output.addfile(normalized, stream)
                else:
                    output.addfile(normalized)
    return excluded


def collect(resources: Path = RESOURCES) -> None:
    manifest = read_json(MANIFEST)
    inputs = BUILD / "onnx-source-inputs"
    destination = BUILD / "sources/onnxruntime"
    destination.mkdir(parents=True, exist_ok=True)
    notices = resources / "notices/onnx-native"
    records = []
    for entry in manifest["archives"]:
        original = inputs / entry["filename"]
        fetch(entry, original)
        if entry.get("recipeArchiveSha512"):
            with original.open("rb") as stream:
                if (
                    hashlib.file_digest(stream, "sha512").hexdigest()
                    != entry["recipeArchiveSha512"]
                ):
                    raise ValueError("Upstream ONNX port archive differs")
        target = destination / (entry["name"] + ".tar")
        excluded = source_tree(original, target)
        if digest(target) != entry["preferredSourceSha256"]:
            raise ValueError("Preferred ONNX source tree differs")
        with tarfile.open(original) as archive:
            for relative, expected in entry["licenseFiles"].items():
                path = PurePosixPath(relative)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in relative
                    or ":" in relative
                ):
                    raise ValueError("Unsafe ONNX notice path")
                member = archive.getmember(entry["archiveRoot"] + "/" + relative)
                if not member.isfile():
                    raise ValueError("ONNX notice is not a regular original file")
                data = archive.extractfile(member).read()
                if hashlib.sha256(data).hexdigest() != expected:
                    raise ValueError("ONNX original notice differs")
                path = notices / entry["name"] / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        records.append(
            {
                "name": entry["name"],
                "originalSha256": digest(original),
                "preferredSourceSha256": digest(target),
                "excluded": excluded,
            }
        )
    for entry in manifest["portFiles"]:
        # Git blobs bind the older FlatBuffers override missing from root ports.
        with urlopen(entry["url"], timeout=30) as response:
            blob = json.load(response)
        data = base64.b64decode(blob["content"], validate=False)
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Original ONNX port bytes differ")
        path = destination / "flatbuffers-port" / entry["filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    record = {
        "manifestSha256": digest(MANIFEST),
        "recipeSha256": digest(Path(__file__)),
        "sources": records,
        "sourceCoverageApproved": False,
        "publicDistributionApproved": False,
    }
    write_json(destination / "source-preparation.json", record)
    write_json(notices / "source-preparation.json", record)
    shutil.copy2(MANIFEST, destination / MANIFEST.name)
    shutil.copy2(MANIFEST, notices / MANIFEST.name)
    shutil.copy2(Path(__file__), destination / Path(__file__).name)


if __name__ == "__main__":
    collect()
