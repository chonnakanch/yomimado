"""Smoke-test the exact installed Windows service with fresh data and no developer PATH."""

from __future__ import annotations

import argparse
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image


def observed_cpu_inference(names: set[str], onnx_backend: bool) -> bool:
    # The wheel uses cv2.pyd; the audited CPython 3.11 x64 build preserves its
    # ABI filename. Module paths and hashes are checked separately below.
    opencv = bool(names & {"cv2.pyd", "cv2.cp311-win_amd64.pyd"})
    backend = (
        "onnxruntime_pybind11_state.pyd" in names
        if onnx_backend
        else "torch_cpu.dll" in names
    )
    return opencv and backend


def loaded_modules(pid: int, runtime: Path) -> list[dict]:
    """Check libraries actually loaded after inference, not just PE imports."""
    system = Path(os.environ["SystemRoot"]).resolve()
    powershell = system / "System32/WindowsPowerShell/v1.0/powershell.exe"
    script = (
        "$ErrorActionPreference='Stop'; [Console]::OutputEncoding="
        "[System.Text.UTF8Encoding]::new($false); "
        f"@(Get-Process -Id {pid}).Modules | "
        "ForEach-Object { @{ path=$_.FileName; name=$_.ModuleName; "
        "sha256=(Get-FileHash $_.FileName -Algorithm SHA256).Hash.ToLower() } } | "
        "ConvertTo-Json -Compress"
    )
    modules = json.loads(
        subprocess.check_output(
            [str(powershell), "-NoProfile", "-NonInteractive", "-Command", script],
            text=True,
            encoding="utf-8",
            # A Python child of pwsh inherits PS7 modules, incompatible with
            # Windows PowerShell. Let the OS shell construct its own module path.
            env={k: v for k, v in os.environ.items() if k.upper() != "PSMODULEPATH"},
        )
    )
    for item in modules:
        path = Path(item["path"]).resolve()
        if not path.is_relative_to(runtime.resolve()) and not path.is_relative_to(
            system
        ):
            raise RuntimeError(
                "Frozen runtime loaded an external native module: " + str(path)
            )
        name = item["name"].lower()
        windows_cpp = name == "msvcp_win.dll" and path.parent == system / "System32"
        if (
            not windows_cpp
            and name.startswith(
                ("vcruntime", "msvcp", "vcomp", "concrt", "libiomp", "mkl")
            )
            and not path.is_relative_to(runtime.resolve())
        ):
            raise RuntimeError(
                "Frozen runtime used a system/developer copy instead of its app-local library: "
                + name
            )
        if "cuda" in name or "cudnn" in name:
            raise RuntimeError("CPU inference loaded CUDA")
    return modules


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("installed", type=Path)
    parser.add_argument("--detector-model", type=Path, required=True)
    args = parser.parse_args()
    resources = args.installed.resolve() / "ocr"
    if sys.platform != "win32":
        raise ValueError("Installed Windows smoke must run on Windows")
    assets = resources / "assets"
    detector = args.detector_model.resolve()
    expected = "1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f"
    # Use the same pinned publisher asset as the desktop import flow.
    import hashlib

    if hashlib.sha256(detector.read_bytes()).hexdigest() != expected:
        raise ValueError("Detector model is not the pinned publisher file")
    with tempfile.TemporaryDirectory(prefix="yomimado-smoke-") as temporary:
        data = Path(temporary)
        with socket.socket() as port_socket:
            port_socket.bind(("127.0.0.1", 0))
            port = port_socket.getsockname()[1]
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("YOMIMADO_") and key != "PYTHONPATH"
        }
        env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
        env.pop("PYTHONHOME", None)
        env.update(
            {
                "YOMIMADO_OCR_PORT": str(port),
                "YOMIMADO_DETECTOR_REPO": str(assets / "comic-text-detector"),
                "YOMIMADO_DETECTOR_MODEL": str(detector),
                "YOMIMADO_MANGA_OCR_MODEL": str(assets / "manga-ocr-base"),
                "YOMIMADO_TRANSLATION_MODEL": str(assets / "opus-mt-ja-en"),
                "YOMIMADO_JMDICT": str(assets / "JMdict_e.gz"),
                "YOMIMADO_KANJIDIC2": str(assets / "kanjidic2.xml.gz"),
                "YOMIMADO_JMDICT_INDEX": str(data / "jmdict.sqlite3"),
                "YOMIMADO_VOCAB_DB": str(data / "vocabulary.sqlite3"),
                "YOMIMADO_TRANSLATION_CACHE": str(data / "translation.sqlite3"),
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "HF_HOME": str(data / "hf"),
                "CUDA_VISIBLE_DEVICES": "",
            }
        )

        def request(
            path: str,
            payload: dict | None = None,
            *,
            body: bytes | None = None,
            content_type: str = "application/json",
        ) -> dict:
            if payload is not None:
                body = json.dumps(payload).encode()
            req = Request(
                f"http://127.0.0.1:{port}{path}",
                data=body,
                headers={"Content-Type": content_type},
            )
            try:
                with urlopen(req, timeout=240) as response:
                    return json.load(response)
            except HTTPError as error:
                # Only synthetic test text is sent by this smoke. Preserve the
                # API's diagnostic instead of reporting an opaque status code.
                raise RuntimeError(
                    f"{path}: HTTP {error.code}: {error.read().decode()}"
                ) from error

        def check(condition: bool, message: str) -> None:
            if not condition:
                raise RuntimeError(message)

        for launch in range(2):
            with (data / "service.log").open("w") as log:
                process = subprocess.Popen(
                    [str(resources / "runtime/yomimado-ocr.exe")],
                    cwd=data,
                    env=env,
                    stdout=log,
                    stderr=log,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                try:
                    deadline = time.monotonic() + 180
                    while True:
                        check(
                            process.poll() is None,
                            "Frozen service exited during startup",
                        )
                        try:
                            health = request("/health")
                            check(
                                health == {"status": "ok", "ocr": "manga"},
                                "Expected the real OCR engine",
                            )
                            break
                        except URLError:
                            check(
                                time.monotonic() < deadline,
                                "Frozen service startup timed out",
                            )
                            time.sleep(0.5)
                    if launch == 1:
                        check(
                            len(request("/api/v1/vocabulary")["words"]) == 1,
                            "Saved word did not survive restart",
                        )
                        check(
                            len(request("/api/v1/sentences")["sentences"]) == 1,
                            "Saved sentence did not survive restart",
                        )
                        check(
                            request(
                                "/api/v1/translate", {"text": "今日は学校に行きます。"}
                            )["cached"],
                            "Translation cache did not survive restart",
                        )
                        continue
                    for orientation in ("vertical", "horizontal"):
                        image = Image.open(
                            Path(__file__).parent
                            / "fixtures"
                            / f"windows-ocr-{orientation}.png"
                        )
                        encoded = io.BytesIO()
                        image.save(encoded, format="PNG")
                        boundary = "YomiMadoSyntheticSmoke"
                        body = (
                            f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="synthetic.png"\r\nContent-Type: image/png\r\n\r\n'.encode()
                            + encoded.getvalue()
                            + f"\r\n--{boundary}--\r\n".encode()
                        )
                        ocr = request(
                            "/api/v1/ocr",
                            body=body,
                            content_type=f"multipart/form-data; boundary={boundary}",
                        )
                        check(
                            ocr["engine"] == "manga"
                            and any(
                                "学校" in r["text"]
                                and len(r["polygon"]) >= 3
                                and r["orientation"] == orientation
                                and all(
                                    0 <= point["x"] <= image.width
                                    and 0 <= point["y"] <= image.height
                                    for point in r["polygon"]
                                )
                                for r in ocr["regions"]
                            ),
                            f"Synthetic {orientation} OCR/geometry failed: {ocr}",
                        )
                    tokens = request(
                        "/api/v1/tokenize", {"text": "今日は学校に行きます。"}
                    )["tokens"]
                    check(
                        any(
                            t["dictionaryForm"] == "学校" and t["reading"]
                            for t in tokens
                        ),
                        "Sudachi tokenization failed",
                    )
                    word = request(
                        "/api/v1/word",
                        {
                            "surface": "学校",
                            "dictionaryForm": "学校",
                            "reading": "ガッコウ",
                        },
                    )
                    check(bool(word["entries"]), "JMdict lookup failed")
                    kanji = request("/api/v1/kanji", {"character": "学"})
                    check(
                        bool(kanji["meanings"]) and bool(kanji["onReadings"]),
                        "KANJIDIC2 lookup failed",
                    )
                    translation = request(
                        "/api/v1/translate", {"text": "今日は学校に行きます。"}
                    )
                    check(
                        bool(translation["translatedText"])
                        and not translation["cached"],
                        "Local translation failed",
                    )
                    request(
                        "/api/v1/vocabulary",
                        {
                            "surface": "学校",
                            "dictionaryForm": "学校",
                            "reading": "ガッコウ",
                            "meanings": ["school"],
                            "sourceText": "今日は学校に行きます。",
                        },
                    )
                    request(
                        "/api/v1/sentences",
                        {
                            "sourceText": translation["sourceText"],
                            "translatedText": translation["translatedText"],
                        },
                    )
                    modules = loaded_modules(process.pid, resources / "runtime")
                    names = {m["name"].lower() for m in modules}
                    onnx_backend = (resources / "assets/onnx/export.json").is_file()
                    check(
                        observed_cpu_inference(names, onnx_backend),
                        "Actual CPU/native inference modules were not observed",
                    )
                    if onnx_backend:
                        check(
                            not any(
                                any(
                                    part in name
                                    for part in ("torch", "cuda", "cudnn", "mkl")
                                )
                                for name in names
                            ),
                            "Unexpected Torch/CUDA/MKL module in the ONNX runtime",
                        )
                    report = {
                        "backend": "onnx" if onnx_backend else "torch",
                        "installedRuntime": str(resources / "runtime"),
                        "runtimeSha256": hashlib.sha256(
                            (resources / "runtime/yomimado-ocr.exe").read_bytes()
                        ).hexdigest(),
                        "loadedModules": modules,
                        "geometry": ["vertical", "horizontal"],
                        "tokenization": True,
                        "dictionaries": True,
                        "kanji": True,
                        "uncachedTranslation": True,
                        "windows11HardwareVerified": False,
                    }
                    (
                        Path(__file__).parent.parent
                        / "services/ocr/build/windows/installed-smoke.json"
                    ).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                except Exception:
                    # This service processes only the generated test text and
                    # isolated databases; surface startup diagnostics on failure.
                    print(
                        (data / "service.log").read_text(
                            encoding="utf-8", errors="replace"
                        )[-8000:],
                        file=sys.stderr,
                    )
                    raise
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
    report_path = (
        Path(__file__).parent.parent / "services/ocr/build/windows/installed-smoke.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["savedDataAndTranslationCacheSurvivedRestart"] = True
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        "PASS: installed frozen health, vertical/horizontal OCR geometry, Sudachi, JMdict, KANJIDIC2, translation and saved-data/cache restart"
    )


if __name__ == "__main__":
    main()
