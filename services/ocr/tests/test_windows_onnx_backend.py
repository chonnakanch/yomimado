import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import windows_onnx_backend as backend


@pytest.fixture(autouse=True)
def clear_backend_caches():
    backend.verified_exports.cache_clear()
    backend.cpu_models.cache_clear()
    backend.translation_provider.cache_clear()
    yield
    backend.verified_exports.cache_clear()
    backend.cpu_models.cache_clear()
    backend.translation_provider.cache_clear()


def graphs(directory: Path):
    directory.mkdir(parents=True)
    outputs = {}
    for name in backend.GRAPH_FILES:
        data = ("synthetic checksum fixture: " + name).encode()
        (directory / name).write_bytes(data)
        outputs[name] = hashlib.sha256(data).hexdigest()
    (directory / "export.json").write_text(json.dumps({"outputs": outputs}), encoding="utf-8")


def test_identity_survives_install_path_changes_and_detects_modified_graph(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    graphs(first)
    graphs(second)
    assert backend.verified_exports(first) == backend.verified_exports(second)
    backend.verified_exports.cache_clear()
    (second / "translation-decoder.onnx").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum differs"):
        backend.verified_exports(second)


def test_export_manifest_cannot_select_extra_or_escaping_files(tmp_path):
    graphs(tmp_path / "onnx")
    path = tmp_path / "onnx/export.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["outputs"]["../unexpected.onnx"] = "0" * 64
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="graph set"):
        backend.verified_exports(path.parent)


def test_translator_is_lazy_and_rejects_missing_configuration(monkeypatch):
    monkeypatch.delenv("YOMIMADO_TRANSLATION_MODEL", raising=False)
    provider = backend.WindowsOnnxTranslator()
    with pytest.raises(FileNotFoundError, match="not configured"):
        _ = provider.identity
    assert backend.translation_provider.cache_info().currsize == 0


def test_backend_cannot_replace_macos_runtime(monkeypatch):
    monkeypatch.setattr(backend, "HOST_PLATFORM", "darwin")
    with pytest.raises(RuntimeError, match="restricted to Windows"):
        backend.configure_backend()


def test_windows_assembly_preserves_routes_and_does_not_load_models(monkeypatch, tmp_path):
    from app.api import translation
    from app.pipeline import real_ocr

    old_models, old_service = real_ocr._models, translation.service
    monkeypatch.setattr(real_ocr, "_models", old_models)
    monkeypatch.setattr(translation, "service", old_service)
    monkeypatch.setattr(backend, "HOST_PLATFORM", "win32")
    monkeypatch.setenv("YOMIMADO_TRANSLATION_CACHE", str(tmp_path / "cache.sqlite3"))
    monkeypatch.setenv("USE_TORCH", "1")
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "0")
    telemetry = []
    monkeypatch.setitem(
        sys.modules,
        "onnxruntime",
        SimpleNamespace(disable_telemetry_events=lambda: telemetry.append(False)),
    )
    routes = list(translation.router.routes)
    backend.configure_backend()
    assert real_ocr._models is backend.cpu_models
    assert isinstance(translation.service.provider, backend.WindowsOnnxTranslator)
    assert translation.router.routes == routes
    assert telemetry == [False]
    assert backend.cpu_models.cache_info().currsize == 0
    assert not (tmp_path / "cache.sqlite3").exists()
