from struct import pack
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.pipeline.real_ocr import _polygon

client = TestClient(app)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + pack(">II", 200, 300)


def test_health_reports_demo_status() -> None:
    assert client.get("/health").json() == {"status": "ok", "ocr": "demo"}


def test_ocr_returns_geometry_first_response() -> None:
    response = client.post(
        "/api/v1/ocr", files={"image": ("capture.png", PNG, "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "regions" in data
    assert data["engine"] == "demo"
    assert len(data["regions"]) == 1
    region = data["regions"][0]
    assert region["id"] == "selection-boundary-demo"
    assert region["confidence"] == 0
    assert region["polygon"] == [
        {"x": 0, "y": 0},
        {"x": 200, "y": 0},
        {"x": 200, "y": 300},
        {"x": 0, "y": 300},
    ]


def test_ocr_rejects_non_images() -> None:
    response = client.post("/api/v1/ocr", files={"image": ("capture.txt", b"text", "text/plain")})
    assert response.status_code == 415


def test_ocr_rejects_invalid_png() -> None:
    response = client.post(
        "/api/v1/ocr", files={"image": ("capture.png", b"not a png", "image/png")}
    )
    assert response.status_code == 422


def test_detector_box_maps_to_image_polygon() -> None:
    block = SimpleNamespace(lines=[], xyxy=[10, 20, 30, 80])
    assert [(point.x, point.y) for point in _polygon(block)] == [
        (10, 20),
        (30, 20),
        (30, 80),
        (10, 80),
    ]
