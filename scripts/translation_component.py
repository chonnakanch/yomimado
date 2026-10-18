"""Build and verify optional, versioned translation downloads outside installers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/ocr"))
from app.translation_resources import digest, read_manifest

MANIFEST = "translation-component.json"


def filename(version: str, backend: str) -> str:
    return f"YomiMado_{version}_translation_{backend}.zip"


def pins() -> dict[str, str]:
    return {
        item["path"]: item["sha256"]
        for item in json.loads((ROOT / "services/ocr/windows-assets.json").read_text())
        if item["path"].startswith("opus-mt-ja-en/")
    }


def copy_component(manifest: Path, source: Path, destination: Path) -> str:
    record = read_manifest(manifest)
    name = record["archive"]["url"].rsplit("/", 1)[1]
    archive = source / name
    if (
        archive.stat().st_size != record["archive"]["bytes"]
        or digest(archive) != record["archive"]["sha256"]
    ):
        raise ValueError("Optional translation release archive differs")
    shutil.copyfile(archive, destination / name)
    return name


def install_smoke_component(manifest: Path, data: Path) -> None:
    """Verify an unpublished component offline during exact-candidate smoke."""
    from app.translation_resources import TranslationResources

    record = read_manifest(manifest)
    name = record["archive"]["url"].rsplit("/", 1)[1]
    default = (
        ROOT
        / "services/ocr/build"
        / (
            "windows/translation-components"
            if record["backend"] == "onnx"
            else "translation-components"
        )
        / name
    )
    archive = Path(os.environ.get("YOMIMADO_SMOKE_TRANSLATION_ARCHIVE", str(default)))
    root = data / "translation-models"
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        TranslationResources(manifest, root).install_archive(
            archive, Path(temporary) / "staged"
        )


def prepare(resources: Path, output: Path, version: str, backend: str) -> Path:
    assets = resources / "assets"
    originals = pins()
    members = {}
    omitted = dict(originals)
    for name, sha in originals.items():
        source = assets / name
        if backend == "onnx" and name.endswith("pytorch_model.bin"):
            # Already verified and moved out by windows_export_inputs.prune().
            continue
        if digest(source) != sha:
            raise ValueError("Changed optional translation input: " + name)
        members["model/" + Path(name).name] = source
    source_export = None
    if backend == "onnx":
        from windows_release import derived_onnx_graphs

        derived_onnx_graphs(resources)
        exported = assets / "onnx"
        source_export = digest(exported / "export.json")
        record = json.loads((exported / "export.json").read_text())
        for name in (
            "translation-encoder.onnx",
            "translation-decoder.onnx",
            "policies.json",
        ):
            members["onnx/" + name] = exported / name
            if name != "policies.json":
                omitted["onnx/" + name] = record["outputs"][name]
        # The complete original export provenance remains in installer notices.
        # The downloaded provider verifies just these two graphs and policy.
        output.mkdir(parents=True, exist_ok=True)
        export = output / "translation-export.json"
        export.write_text(
            json.dumps(
                {
                    "outputs": {
                        name: record["outputs"][name]
                        for name in (
                            "translation-encoder.onnx",
                            "translation-decoder.onnx",
                            "policies.json",
                        )
                    },
                    "sourceExportSha256": source_export,
                },
                indent=2,
            )
            + "\n"
        )
        members["onnx/export.json"] = export
    elif backend != "torch":
        raise ValueError("Unknown translation backend")
    members["notices/Apache-2.0.txt"] = (
        ROOT / "THIRD_PARTY_LICENSES/upstream/assets/Apache-2.0.txt"
    )
    files = {
        name: {"sha256": digest(path), "bytes": path.stat().st_size}
        for name, path in sorted(members.items())
    }
    output.mkdir(parents=True, exist_ok=True)
    archive = output / filename(version, backend)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        for name, source in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            with (
                source.open("rb") as stream,
                bundle.open(info, "w", force_zip64=True) as target,
            ):
                shutil.copyfileobj(stream, target)
    manifest = {
        "schemaVersion": 1,
        "backend": backend,
        "id": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
        "files": files,
        "archive": {
            "url": f"https://github.com/chonnakanch/yomimado/releases/download/v{version}/{archive.name}",
            "sha256": digest(archive),
            "bytes": archive.stat().st_size,
        },
        "excludedAssets": omitted,
        "sourceExportSha256": source_export,
    }
    path = resources / "notices" / MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    read_manifest(path)
    # Validate everything before changing generated installer resources. Keep
    # original data outside the installer for source/parity and offline testing.
    retained = output / "inputs"
    for name in omitted:
        source = assets / name
        if source.exists():
            target = retained / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
    translation = assets / "opus-mt-ja-en"
    if translation.exists():
        if any(translation.iterdir()):
            raise ValueError("Unexpected files remain in optional translation model")
        translation.rmdir()
    verify_omissions(resources)
    return archive


def verify_omissions(resources: Path) -> dict[str, str]:
    path = resources / "notices" / MANIFEST
    if not path.is_file():
        return {}
    manifest = read_manifest(path)
    expected = pins()
    if manifest["backend"] == "onnx":
        exported = resources / "assets/onnx/export.json"
        record = json.loads(exported.read_text())
        if digest(exported) != manifest["sourceExportSha256"]:
            raise ValueError("Optional translation export provenance differs")
        for name in ("translation-encoder.onnx", "translation-decoder.onnx"):
            expected["onnx/" + name] = record["outputs"][name]
    if manifest["excludedAssets"] != expected:
        raise ValueError("Optional translation exclusion differs from pinned inputs")
    for name, sha in expected.items():
        if (resources / "assets" / name).exists():
            raise ValueError("Optional translation data remains in installer: " + name)
        member = (
            ("onnx/" + Path(name).name)
            if name.startswith("onnx/")
            else "model/" + Path(name).name
        )
        if manifest["backend"] == "onnx" and name.endswith("pytorch_model.bin"):
            continue
        if manifest["files"].get(member, {}).get("sha256") != sha:
            raise ValueError("Optional translation download input differs")
    return expected


def prune_ocr_metadata(runtime: Path) -> None:
    for path in (runtime / "_internal").iterdir():
        name = path.name.lower().replace("-", "_")
        if name.startswith(("unidic_lite", "fugashi")) and name.endswith(".dist_info"):
            shutil.rmtree(path)


def verify_ocr_runtime(runtime: Path) -> None:
    for path in (runtime / "_internal").iterdir():
        if (
            path.name.lower()
            .replace("-", "_")
            .startswith(("unidic", "fugashi", "mecab", "libmecab"))
        ):
            raise ValueError(
                "Unused OCR dictionary/binding remains in frozen service: " + path.name
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resources", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--version")
    parser.add_argument("--backend", choices=("torch", "onnx"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--prune-ocr", action="store_true")
    args = parser.parse_args()
    if args.prune_ocr:
        prune_ocr_metadata(args.resources / "runtime")
        verify_ocr_runtime(args.resources / "runtime")
    elif args.check:
        verify_omissions(args.resources)
    else:
        if not args.output or not args.version or not args.backend:
            parser.error(
                "Preparing a component requires --output, --version and --backend"
            )
        print(prepare(args.resources, args.output, args.version, args.backend))
