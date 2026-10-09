"""Original CPU tensor checks and actual native imports for source-built Torch."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
import re
import sys
from pathlib import Path

FORBIDDEN = re.compile(
    r"^(?:lib)?(?:mkl|iomp|ipp|cudart|cublas|cudnn|nvrtc)", re.IGNORECASE
)


def verify_inventory(records: list[dict]) -> None:
    if not records or any(
        item["machine"] != "0x8664"
        or any(FORBIDDEN.search(n) for n in item["imports"])
        or FORBIDDEN.search(Path(item["path"]).name)
        for item in records
    ):
        raise ValueError("Non-AMD64 or forbidden Torch native input")


def main() -> None:
    import pefile
    import torch

    if (
        sys.platform != "win32"
        or platform.machine().lower() != "amd64"
        or platform.python_version() != "3.11.17"
    ):
        raise ValueError("Requires source-built Windows x64 Python")
    if (
        torch.__version__ != "2.8.0+cpu"
        or torch.version.git_version != "a1cb3cc05d46d198467bebbb6e8fba50a325d4e7"
        or torch.version.cuda is not None
        or torch.backends.mkl.is_available()
        or torch.backends.openmp.is_available()
        or torch.backends.mkldnn.is_available()
    ):
        raise ValueError("Unexpected Torch version or enabled Intel/GPU backend")
    torch.set_num_threads(1)
    torch.manual_seed(17)
    a = torch.arange(12, dtype=torch.float32).reshape(3, 4)
    product = a @ a.T
    assert torch.equal(
        product,
        torch.tensor([[14.0, 38.0, 62.0], [38.0, 126.0, 214.0], [62.0, 214.0, 366.0]]),
    )
    image = torch.randn(2, 3, 16, 16)
    convolution = torch.nn.Conv2d(3, 8, 3)(image)
    assert convolution.shape == (2, 8, 14, 14) and torch.isfinite(convolution).all()
    attention = torch.nn.MultiheadAttention(8, 2, batch_first=True).eval()
    sequence = torch.randn(2, 7, 8)
    with torch.inference_mode():
        output, _ = attention(sequence, sequence, sequence)
    assert output.shape == sequence.shape and torch.isfinite(output).all()
    spec = importlib.util.spec_from_file_location(
        "opencv_native_modules", Path(__file__).with_name("opencv-windows-probe.py")
    )
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)
    loaded = collector.loaded_modules()
    for item in loaded:
        if FORBIDDEN.search(Path(item["path"]).name):
            raise ValueError("Forbidden actual loaded native dependency")
    directory = Path(torch.__file__).parent.resolve()
    records = []
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
                        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])
                    }
                    | {
                        entry.dll.decode().lower()
                        for entry in getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", [])
                    }
                ),
            }
        )
        pe.close()
    verify_inventory(records)
    hashes = {
        str(Path(item["path"]).resolve()).lower(): item["sha256"] for item in loaded
    }
    required = [
        item
        for item in records
        if Path(item["path"]).name.lower()
        in {"torch_cpu.dll", "torch_python.dll", "c10.dll"}
    ]
    if len(required) != 3 or any(
        hashes.get(item["path"].lower()) != item["sha256"] for item in required
    ):
        raise ValueError("Built Torch DLLs not loaded from exact installed wheel")
    report = {
        "passed": True,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "gitVersion": torch.version.git_version,
        "buildConfiguration": torch.__config__.show(),
        "tensorChecks": ["matrix multiplication", "CPU convolution", "CPU attention"],
        "nativeInventory": records,
        "loadedModules": loaded,
        "installedRuntimeVerified": False,
        "sourceCoverageApproved": False,
    }
    Path(sys.argv[1]).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
