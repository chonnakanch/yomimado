"""Smoke-test the frozen service from an exact .app using isolated local data."""

from __future__ import annotations

import argparse
import io
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path)
    parser.add_argument("--detector-model", type=Path, required=True)
    args = parser.parse_args()
    resources = args.app.resolve() / "Contents/Resources/ocr"
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
                    [str(resources / "runtime/yomimado-ocr")],
                    cwd=data,
                    env=env,
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
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
                    font = ImageFont.truetype(
                        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 48
                    )
                    image = Image.new("RGB", (100, 240), "white")
                    draw = ImageDraw.Draw(image)
                    # The pipeline deliberately declines two-character whole-
                    # selection guesses when the detector supplies no box.
                    for index, character in enumerate("学校へ"):
                        draw.text(
                            (25, 20 + index * 60),
                            character,
                            font=font,
                            fill="black",
                            anchor="lt",
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
                            "学校" in r["text"] and len(r["polygon"]) >= 3
                            for r in ocr["regions"]
                        ),
                        f"Synthetic vertical OCR/geometry failed: {ocr}",
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
                except Exception:
                    # This service processes only the generated test text and
                    # isolated databases; surface startup diagnostics on failure.
                    print((data / "service.log").read_text()[-8000:], file=sys.stderr)
                    raise
                finally:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        process.wait()
    print(
        "PASS: frozen health, vertical OCR geometry, Sudachi, JMdict, KANJIDIC2, translation and saved-data/cache restart"
    )


if __name__ == "__main__":
    main()
