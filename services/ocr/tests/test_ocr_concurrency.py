import asyncio
import importlib
import threading
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

from app.main import app
from app.models import OcrResponse

ocr_api = importlib.import_module("app.api.ocr")


def test_overlapping_requests_are_rejected_without_entering_models(monkeypatch):
    started, release = threading.Event(), threading.Event()
    calls = []

    def recognize(image):
        calls.append(image.image_bytes)
        if len(calls) == 1:
            started.set()
            assert release.wait(5), "test did not release the first inference"
        return OcrResponse(regions=[], engine="manga")

    monkeypatch.setattr(ocr_api.pipeline, "recognize", recognize)
    with TestClient(
        app, base_url="http://127.0.0.1", headers={"X-YomiMado-Client": "desktop"}
    ) as client:

        def post():
            return client.post(
                "/api/v1/ocr", files={"image": ("synthetic.png", b"synthetic", "image/png")}
            )

        with ThreadPoolExecutor(max_workers=1) as executor:
            first = executor.submit(post)
            try:
                assert started.wait(3)
                busy = post()
                assert busy.status_code == 503
                assert busy.headers["retry-after"] == "1"
                assert "another scan" in busy.json()["detail"]
                assert len(calls) == 1
            finally:
                release.set()
            assert first.result(timeout=3).status_code == 200
        assert post().status_code == 200
    assert len(calls) == 2


@pytest.mark.parametrize(
    "failure,status", [(ValueError("invalid"), 422), (RuntimeError("model"), 503)]
)
def test_failed_inference_releases_admission(monkeypatch, failure, status):
    calls = 0

    def recognize(_image):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise failure
        return OcrResponse(regions=[], engine="manga")

    monkeypatch.setattr(ocr_api.pipeline, "recognize", recognize)
    with TestClient(
        app, base_url="http://127.0.0.1", headers={"X-YomiMado-Client": "desktop"}
    ) as client:
        for expected in (status, 200):
            response = client.post(
                "/api/v1/ocr", files={"image": ("synthetic.png", b"synthetic", "image/png")}
            )
            assert response.status_code == expected


def test_cancelled_request_keeps_models_exclusive_until_worker_finishes(monkeypatch):
    started, release, finished = threading.Event(), threading.Event(), threading.Event()
    calls = 0

    def recognize(_image):
        nonlocal calls
        calls += 1
        if calls == 1:
            started.set()
            try:
                assert release.wait(5), "test did not release the cancelled inference"
            finally:
                finished.set()
        return OcrResponse(regions=[], engine="manga")

    monkeypatch.setattr(ocr_api.pipeline, "recognize", recognize)

    async def request():
        return await ocr_api.ocr(
            image=UploadFile(
                filename="synthetic.png",
                file=BytesIO(b"synthetic"),
                headers=Headers({"content-type": "image/png"}),
            ),
            debug=False,
        )

    async def exercise():
        first = asyncio.create_task(request())
        try:
            assert await asyncio.to_thread(started.wait, 3)
            first.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first
            with pytest.raises(HTTPException) as busy:
                await request()
            assert busy.value.status_code == 503
            assert calls == 1
        finally:
            release.set()
            await asyncio.to_thread(finished.wait, 3)
            await asyncio.gather(first, return_exceptions=True)
        # The endpoint's cancelled await is separate from its still-running
        # worker. Allow that worker's final lock release to reach completion.
        for _ in range(100):
            try:
                return await request()
            except HTTPException as error:
                assert error.status_code == 503
                await asyncio.sleep(0.01)
        pytest.fail("inference admission stayed locked after worker completion")

    assert asyncio.run(exercise()).engine == "manga"
    assert calls == 2
