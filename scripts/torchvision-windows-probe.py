"""Exercise the rebuilt CPU operator ABI and OCR's Pillow-backed transforms."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
import sys
from pathlib import Path


def verify_versions(torch, vision) -> None:
    if (
        torch.__version__ != "2.8.0+cpu"
        or torch.version.git_version != "a1cb3cc05d46d198467bebbb6e8fba50a325d4e7"
        or torch.version.cuda is not None
        or vision.__version__ != "0.23.0+cpu"
        or vision.version.git_version != "824e8c8726b65fd9d5abdc9702f81c2b0c4c0dc8"
        or not vision.extension._has_ops()
        or vision.extension._check_cuda_version() != -1
    ):
        raise ValueError("Unexpected Torch/torchvision source or CPU operator ABI")


def main() -> None:
    import pefile
    import torch
    import torchvision as vision
    from PIL import Image

    if (
        sys.platform != "win32"
        or platform.machine().lower() != "amd64"
        or platform.python_version() != "3.11.17"
    ):
        raise ValueError("Requires source-built Windows x64 Python")
    verify_versions(torch, vision)
    torch.set_num_threads(1)
    boxes = torch.tensor(
        [[0.0, 0.0, 10.0, 10.0], [1.0, 1.0, 9.0, 9.0], [20.0, 20.0, 30.0, 30.0]]
    )
    scores = torch.tensor([0.9, 0.8, 0.7])
    assert vision.ops.nms(boxes, scores, 0.5).tolist() == [0, 2]
    transforms = vision.transforms.Compose(
        [
            vision.transforms.Resize((16, 24)),
            vision.transforms.ToTensor(),
            vision.transforms.Normalize([0.5] * 3, [0.5] * 3),
        ]
    )
    tensor = transforms(Image.new("RGB", (12, 8), (128, 128, 128)))
    assert tensor.shape == (3, 16, 24)
    assert torch.allclose(tensor, torch.full_like(tensor, (128 / 255 - 0.5) / 0.5))
    spec = importlib.util.spec_from_file_location(
        "torch_native_guard", Path(__file__).with_name("torch-windows-probe.py")
    )
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    spec = importlib.util.spec_from_file_location(
        "opencv_native_modules", Path(__file__).with_name("opencv-windows-probe.py")
    )
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)
    loaded = collector.loaded_modules()
    if any(guard.FORBIDDEN.search(Path(item["path"]).name) for item in loaded):
        raise ValueError("Forbidden actual loaded native dependency")
    records = []
    directory = Path(vision.__file__).parent.resolve()
    for path in sorted(directory.rglob("*")):
        if path.suffix.lower() not in {".dll", ".pyd", ".exe"}:
            continue
        pe = pefile.PE(str(path))
        records.append(
            {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "machine": hex(pe.FILE_HEADER.Machine),
                "imports": sorted(
                    {
                        entry.dll.decode().lower()
                        for table in (
                            "DIRECTORY_ENTRY_IMPORT",
                            "DIRECTORY_ENTRY_DELAY_IMPORT",
                        )
                        for entry in getattr(pe, table, [])
                    }
                ),
            }
        )
        pe.close()
    guard.verify_inventory(records)
    # Pillow supplies image transforms; omit unused image/video native codecs.
    if len(records) != 1 or Path(records[0]["path"]).name.lower() != "_c.pyd":
        raise ValueError("Unexpected torchvision native extensions")
    hashes = {
        str(Path(item["path"]).resolve()).lower(): item["sha256"] for item in loaded
    }
    if hashes.get(records[0]["path"].lower()) != records[0]["sha256"]:
        raise ValueError("Exact installed torchvision operator extension not loaded")
    report = {
        "passed": True,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "torchvision": vision.__version__,
        "gitVersion": vision.version.git_version,
        "checks": ["CPU NMS known selection", "Pillow resize/tensor/normalization"],
        "nativeInventory": records,
        "loadedModules": loaded,
        "installedRuntimeVerified": False,
        "sourceCoverageApproved": False,
    }
    Path(sys.argv[1]).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
