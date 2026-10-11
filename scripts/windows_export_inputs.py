"""Exclude only verified export-only weights from the Windows ONNX installer."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from windows_release import (
    BUILD,
    RESOURCES,
    SERVICE,
    derived_onnx_graphs,
    digest,
    read_json,
    write_json,
)

WEIGHTS = {
    "manga-ocr-base/pytorch_model.bin",
    "opus-mt-ja-en/pytorch_model.bin",
}
RECORD = "windows-export-only-inputs.json"
COMPARISON = "windows-export-comparison.json"


def expected_weights() -> dict[str, str]:
    pins = {
        item["path"]: item["sha256"]
        for item in read_json(SERVICE / "windows-assets.json")
        if item["path"] in WEIGHTS
    }
    if set(pins) != WEIGHTS:
        raise ValueError("Export-only weight pins are incomplete")
    return pins


def check_comparison(path: Path) -> None:
    report = read_json(path)
    if not all(
        report.get(key) is True
        for key in (
            "exactOcrParity",
            "exactTranslationParity",
            "torchAbsentFromOnnxWorker",
        )
    ):
        raise ValueError("Export-only exclusion requires successful inference parity")
    baseline, onnx = (report["results"][k] for k in ("baseline", "onnx"))
    if (
        set(onnx["ocr"]) != {"horizontal", "vertical"}
        or len(onnx["translation"]) < 3
        or baseline["ocr"] != onnx["ocr"]
        or baseline["translation"] != onnx["translation"]
        or onnx["torchImported"] is not False
        or onnx["cacheSurvivedNewService"] is not True
    ):
        raise ValueError("Export-only exclusion comparison is incomplete")


def prune(resources: Path = RESOURCES) -> None:
    graphs = derived_onnx_graphs(resources)
    if len(graphs) != 4:
        raise ValueError("Export-only exclusion requires all four bound ONNX graphs")
    comparison = BUILD / "onnx-comparison/comparison.json"
    check_comparison(comparison)
    pins = expected_weights()
    for relative, sha in pins.items():
        path = resources / "assets" / relative
        if path.is_symlink() or digest(path) != sha:
            raise ValueError("Export-only weight changed: " + relative)
    # Preserve inputs outside installer resources. Validate every input first;
    # never use this operation to excuse a missing or changed runtime asset.
    removed_bytes = 0
    for relative in sorted(pins):
        path = resources / "assets" / relative
        destination = BUILD / "export-only-models" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        removed_bytes += path.stat().st_size
        shutil.move(str(path), str(destination))
    notices = resources / "notices"
    notices.mkdir(parents=True, exist_ok=True)
    shutil.copy2(comparison, notices / COMPARISON)
    write_json(
        notices / RECORD,
        {
            "excludedInputs": pins,
            "removedBytes": removed_bytes,
            "exportSha256": digest(resources / "assets/onnx/export.json"),
            "graphs": {p.name: sha for p, sha in graphs.items()},
            "comparisonSha256": digest(comparison),
            "recipeSha256": digest(Path(__file__)),
            "publicDistributionApproved": False,
        },
    )
    shutil.copy2(Path(__file__), notices / Path(__file__).name)
    verify(resources)
    print(f"Excluded {removed_bytes} bytes of verified export-only weights")


def verify(resources: Path) -> set[str]:
    path = resources / "notices" / RECORD
    if not path.is_file():
        return set()
    record = read_json(path)
    graphs = derived_onnx_graphs(resources)
    if (
        record["excludedInputs"] != expected_weights()
        or len(graphs) != 4
        or record["graphs"] != {p.name: sha for p, sha in graphs.items()}
        or record["exportSha256"] != digest(resources / "assets/onnx/export.json")
        or record["comparisonSha256"] != digest(resources / "notices" / COMPARISON)
        or record["recipeSha256"] != digest(Path(__file__))
        or record["recipeSha256"] != digest(resources / "notices" / Path(__file__).name)
        or any((resources / "assets" / relative).exists() for relative in WEIGHTS)
    ):
        raise ValueError("Unbound Windows export-only exclusion")
    check_comparison(resources / "notices" / COMPARISON)
    return WEIGHTS.copy()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resources", type=Path, default=RESOURCES)
    args = parser.parse_args()
    prune(args.resources)
