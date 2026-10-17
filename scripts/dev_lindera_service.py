"""Launch the local Lindera experiment with OCR, dictionary and translation paths.

Uses existing local assets only. No downloads or packaged-runtime changes.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def configure(root: Path, existing: dict[str, str]) -> dict[str, str]:
    root = root.resolve()
    service = root / "services/ocr"
    experiment = service / "build/lindera-experiment-20261017"
    assets = root / "apps/desktop/src-tauri/resources/ocr/assets"
    data = experiment / "dev-data"
    defaults = {
        "YOMIMADO_LINDERA_DICTIONARY": experiment / "dictionary/lindera-ipadic",
        "YOMIMADO_DETECTOR_REPO": assets / "comic-text-detector",
        "YOMIMADO_DETECTOR_MODEL": service / "local-models/comictextdetector.pt.onnx",
        "YOMIMADO_MANGA_OCR_MODEL": assets / "manga-ocr-base",
        "YOMIMADO_TRANSLATION_MODEL": assets / "opus-mt-ja-en",
        "YOMIMADO_JMDICT": assets / "JMdict_e.gz",
        "YOMIMADO_KANJIDIC2": assets / "kanjidic2.xml.gz",
        "YOMIMADO_JMDICT_INDEX": data / "jmdict-index.sqlite3",
        "YOMIMADO_TRANSLATION_CACHE": data / "translation.sqlite3",
        "YOMIMADO_VOCAB_DB": data / "vocabulary.sqlite3",
    }
    env = existing | {
        key: existing.get(key) or str(path) for key, path in defaults.items()
    }
    env.update(
        {
            "YOMIMADO_TOKENIZER": "lindera",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        }
    )
    env["PYTHONPATH"] = os.pathsep.join(
        filter(
            None,
            (str(service), str(experiment / "site"), existing.get("PYTHONPATH", "")),
        )
    )
    required = {
        "detector code": Path(env["YOMIMADO_DETECTOR_REPO"]) / "inference.py",
        "detector weights": Path(env["YOMIMADO_DETECTOR_MODEL"]),
        "recognition weights": Path(env["YOMIMADO_MANGA_OCR_MODEL"])
        / "pytorch_model.bin",
        "recognition config": Path(env["YOMIMADO_MANGA_OCR_MODEL"]) / "config.json",
        "Lindera dictionary": Path(env["YOMIMADO_LINDERA_DICTIONARY"])
        / "metadata.json",
    }
    missing = [
        f"{name}: {path}" for name, path in required.items() if not path.is_file()
    ]
    if missing:
        raise RuntimeError("Missing local experiment inputs:\n" + "\n".join(missing))
    return env


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--check", action="store_true", help="Check paths without starting a server"
    )
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    try:
        env = configure(Path(__file__).resolve().parents[1], dict(os.environ))
    except RuntimeError as error:
        parser.exit(1, str(error) + "\n")
    if args.check:
        print(
            "PASS: OCR model paths and Lindera dictionary exist; service configured for manga OCR"
        )
        return
    os.environ.update(env)
    sys.path[:0] = env["PYTHONPATH"].split(os.pathsep)
    import uvicorn

    print(
        f"Starting local manga OCR + Lindera at http://127.0.0.1:{args.port}",
        flush=True,
    )
    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
