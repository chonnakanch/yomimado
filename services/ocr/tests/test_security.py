import asyncio
from struct import pack
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app import security
from app.api import ocr as ocr_api
from app.main import app
from app.models import OcrResponse
from app.pipeline.pipeline import OcrInput, OcrPipeline

CLIENT_HEADERS = {security.CLIENT_HEADER: security.CLIENT_HEADER_VALUE}
client = TestClient(app, base_url="http://127.0.0.1:8765", headers=CLIENT_HEADERS)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + pack(">II", 200, 300)


@pytest.mark.parametrize("origin", ["https://untrusted.example", "null", "http://localhost:9999"])
def test_hostile_upload_is_blocked_before_recognition(monkeypatch, origin):
    recognize = Mock(return_value=OcrResponse(regions=[], engine="demo"))
    monkeypatch.setattr(ocr_api.pipeline, "recognize", recognize)
    response = client.post(
        "/api/v1/ocr",
        headers={"Origin": origin},
        files={"image": ("capture.png", PNG, "image/png")},
    )
    assert response.status_code == 403
    recognize.assert_not_called()


@pytest.mark.parametrize("origin", security.ALLOWED_ORIGINS)
def test_app_and_development_origins_still_work(monkeypatch, origin):
    monkeypatch.setattr(
        ocr_api.pipeline, "recognize", lambda _: OcrResponse(regions=[], engine="demo")
    )
    response = client.post(
        "/api/v1/ocr",
        headers={"Origin": origin},
        files={"image": ("capture.png", PNG, "image/png")},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize("headers", [{}, {security.CLIENT_HEADER: "wrong"}])
def test_api_requires_client_header_even_for_reading_saved_data(headers):
    raw_client = TestClient(app, base_url="http://127.0.0.1:8765")
    response = raw_client.get("/api/v1/vocabulary", headers=headers)
    assert response.status_code == 403


@pytest.mark.parametrize("host", ["untrusted.example", "127.0.0.1.untrusted.example"])
def test_non_loopback_host_cannot_use_service_even_with_client_header(host):
    response = TestClient(app, base_url=f"http://{host}:8765", headers=CLIENT_HEADERS).get(
        "/health"
    )
    assert response.status_code == 400


def test_custom_header_preflight_allows_only_app_origins():
    headers = {
        "Origin": "http://tauri.localhost",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": security.CLIENT_HEADER,
    }
    assert client.options("/api/v1/ocr", headers=headers).status_code == 200
    headers["Origin"] = "https://untrusted.example"
    assert client.options("/api/v1/ocr", headers=headers).status_code == 400


def test_upload_limit_includes_multipart_overhead_before_handler(monkeypatch):
    monkeypatch.setattr(security, "MAX_OCR_REQUEST_BYTES", 128)
    recognize = Mock(return_value=OcrResponse(regions=[], engine="demo"))
    monkeypatch.setattr(ocr_api.pipeline, "recognize", recognize)
    response = client.post("/api/v1/ocr", files={"image": ("capture.png", PNG, "image/png")})
    assert response.status_code == 413
    recognize.assert_not_called()


@pytest.mark.parametrize("content_length", [None, b"1"])
def test_chunked_or_underdeclared_body_cannot_bypass_limit(monkeypatch, content_length):
    monkeypatch.setattr(security, "MAX_JSON_REQUEST_BYTES", 4)
    called = []

    async def endpoint(scope, receive, send):
        called.append(True)

    messages = iter(
        [
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.request", "body": b"45", "more_body": False},
        ]
    )

    async def receive():
        return next(messages)

    sent = []

    async def send(message):
        sent.append(message)

    headers = [(b"x-yomimado-client", b"desktop")]
    if content_length is not None:
        headers.append((b"content-length", content_length))
    scope = {"type": "http", "path": "/api/v1/translate", "headers": headers}
    asyncio.run(security.LocalRequestMiddleware(endpoint)(scope, receive, send))
    assert not called
    assert sent[0]["status"] == 413


def test_bounded_stream_is_replayed_once_without_changing_bytes(monkeypatch):
    monkeypatch.setattr(security, "MAX_JSON_REQUEST_BYTES", 5)
    received = []

    async def endpoint(scope, receive, send):
        received.append(await receive())

    messages = iter(
        [
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.request", "body": b"45", "more_body": False},
        ]
    )

    async def receive():
        return next(messages)

    async def send(message):
        pass

    scope = {"type": "http", "path": "/health", "headers": []}
    asyncio.run(security.LocalRequestMiddleware(endpoint)(scope, receive, send))
    assert received == [{"type": "http.request", "body": b"12345", "more_body": False}]


@pytest.mark.parametrize("dimensions", [(100_000, 100_000), (16_385, 10), (10_000, 5_000)])
def test_pixel_limit_prevents_model_loading(monkeypatch, dimensions):
    from app.pipeline import real_ocr

    monkeypatch.setenv("YOMIMADO_DETECTOR_REPO", "synthetic-path")
    recognize = Mock()
    monkeypatch.setattr(real_ocr, "recognize_with_models", recognize)
    png = PNG[:16] + pack(">II", *dimensions)
    with pytest.raises(ValueError, match="dimensions exceed"):
        OcrPipeline().recognize(OcrInput(image_bytes=png, content_type="image/png"))
    recognize.assert_not_called()


def test_regular_retina_and_8k_dimensions_remain_allowed():
    security.validate_capture_dimensions(5120, 2880)
    security.validate_capture_dimensions(7680, 4320)
