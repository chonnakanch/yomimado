import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import translation_preferences as preferences
from app.main import app
from app.translation import TranslationService


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(preferences, "resources", lambda: SimpleNamespace(root=tmp_path / "data"))
    monkeypatch.delenv("USE_TORCH", raising=False)
    preferences.verify_import.cache_clear()
    yield
    preferences.verify_import.cache_clear()


def model_folder(path: Path):
    path.mkdir()
    (path / "config.json").write_text(json.dumps({"model_type": "marian"}))
    (path / "tokenizer_config.json").write_text(
        json.dumps({"source_lang": "ja", "target_lang": "en"})
    )
    for name in ("vocab.json", "source.spm", "target.spm", "pytorch_model.bin"):
        (path / name).write_bytes(b"synthetic model fixture")
    return path


@pytest.mark.parametrize("legacy", [False, True])
def test_no_default_model_even_when_old_model_files_exist(tmp_path, monkeypatch, legacy):
    from app.api import translation as api

    source = model_folder(tmp_path / "existing-model")
    monkeypatch.setenv("YOMIMADO_TRANSLATION_MODEL", str(source))
    if legacy:
        preferences.save_settings({"provider": "builtin", "ollamaModel": "", "imported": None})
    assert preferences.settings_status()["provider"] == "none"
    monkeypatch.setattr(
        api,
        "service",
        TranslationService(preferences.ConfiguredTranslationProvider(), tmp_path / "cache.db"),
    )
    client = TestClient(app, base_url="http://127.0.0.1", headers={"X-YomiMado-Client": "desktop"})
    response = client.post("/api/v1/translate", json={"text": "学校"})
    assert response.status_code == 503
    assert "import a model or install and select one through Ollama" in response.json()["detail"]


def test_import_copies_validated_model_and_persists_selection(tmp_path, monkeypatch):
    source = model_folder(tmp_path / "my-translator")
    checked = []
    monkeypatch.setattr(preferences, "validate_model", lambda path: checked.append(path))
    status = preferences.import_model(str(source))
    assert status == {
        "provider": "imported",
        "importedModel": "my-translator",
        "ollamaModel": "",
        "backend": "torch",
    }
    managed = preferences.imported_path()
    assert managed != source
    assert (managed / "pytorch_model.bin").read_bytes() == b"synthetic model fixture"
    assert len(checked) == 1
    # Source folders can move after import; managed files remain valid on restart.
    (source / "pytorch_model.bin").unlink()
    preferences.verify_import.cache_clear()
    assert preferences.imported_path() == managed
    assert preferences.settings_status()["provider"] == "imported"
    preferences.save_settings(preferences.read_settings() | {"provider": "none"})
    assert preferences.settings_status()["importedModel"] == "my-translator"
    preferences.select_provider("imported")
    assert preferences.imported_path() == managed


def test_invalid_import_preserves_selected_model(tmp_path, monkeypatch):
    source = model_folder(tmp_path / "valid")
    monkeypatch.setattr(preferences, "validate_model", lambda _: None)
    preferences.import_model(str(source))
    previous = preferences.read_settings()
    invalid = model_folder(tmp_path / "invalid")
    monkeypatch.setattr(
        preferences, "validate_model", lambda _: (_ for _ in ()).throw(RuntimeError("bad weights"))
    )
    with pytest.raises(RuntimeError, match="bad weights"):
        preferences.import_model(str(invalid))
    assert preferences.read_settings() == previous


@pytest.mark.parametrize(
    "change", ["family", "language", "custom-code", "missing", "external-link"]
)
def test_import_rejects_incompatible_or_unsafe_files(tmp_path, monkeypatch, change):
    source = model_folder(tmp_path / "model")
    if change == "family":
        (source / "config.json").write_text('{"model_type":"llama"}')
    elif change == "language":
        (source / "tokenizer_config.json").write_text('{"source_lang":"en","target_lang":"ja"}')
    elif change == "custom-code":
        (source / "tokenizer_config.json").write_text(
            '{"auto_map":{"AutoTokenizer":"custom.Code"}}'
        )
    elif change == "missing":
        (source / "target.spm").unlink()
    else:
        (source / "source.spm").unlink()
        (tmp_path / "outside").write_text("outside")
        (source / "source.spm").symlink_to(tmp_path / "outside")
    monkeypatch.setattr(
        preferences, "validate_model", lambda _: pytest.fail("Must reject before loading")
    )
    with pytest.raises((ValueError, FileNotFoundError)):
        preferences.import_model(str(source))
    assert preferences.settings_status()["provider"] == "none"


def test_modified_import_is_rejected_after_restart(tmp_path, monkeypatch):
    source = model_folder(tmp_path / "model")
    monkeypatch.setattr(preferences, "validate_model", lambda _: None)
    preferences.import_model(str(source))
    (preferences.imported_path() / "pytorch_model.bin").write_bytes(b"changed")
    preferences.verify_import.cache_clear()
    with pytest.raises(ValueError, match="has changed"):
        preferences.imported_path()


def test_windows_import_requires_onnx_graphs_not_torch_weights(tmp_path, monkeypatch):
    source = model_folder(tmp_path / "model")
    monkeypatch.setenv("USE_TORCH", "0")
    with pytest.raises(FileNotFoundError):
        preferences.collect_files(source)
    onnx = tmp_path / "onnx"
    onnx.mkdir()
    for name in preferences.ONNX_FILES:
        (onnx / name).write_text("synthetic graph fixture")
    (onnx / "policies.json").write_text('{"translation":{"beams":6,"limit":257}}')
    files = preferences.collect_files(tmp_path)
    # Select the export parent containing both model/ and onnx/.
    assert "model/pytorch_model.bin" not in files


def test_requests_snapshot_provider_and_keep_cache_separate(tmp_path, monkeypatch):
    from app import ollama_translation

    current = {"provider": "ollama", "ollamaModel": "first:latest"}
    monkeypatch.setattr(preferences, "read_settings", lambda: current.copy())
    calls = []

    class Provider:
        def __init__(self, name):
            self.name = name

        @property
        def identity(self):
            # Simulate switching settings while a request is underway.
            current["ollamaModel"] = "second:latest"
            return self.name

        def translate(self, text):
            calls.append(self.name)
            return self.name

    monkeypatch.setattr(ollama_translation, "OllamaProvider", Provider)
    service = TranslationService(preferences.ConfiguredTranslationProvider(), tmp_path / "cache.db")
    assert service.translate("学校").translatedText == "first:latest"
    assert service.translate("学校").translatedText == "second:latest"
    assert service.translate("学校").cached is True
    assert calls == ["first:latest", "second:latest"]


def test_selection_requires_installed_local_ollama_model(monkeypatch):
    from app import ollama_translation

    monkeypatch.setattr(ollama_translation, "local_model", lambda name: {"name": name + ":latest"})
    assert preferences.select_provider("ollama", "chosen")["ollamaModel"] == "chosen:latest"
    assert preferences.read_settings()["provider"] == "ollama"


def test_settings_routes_do_not_bypass_desktop_request_guard():
    client = TestClient(app, base_url="http://127.0.0.1")
    for path in ("/api/v1/translation-settings", "/api/v1/translation-settings/ollama"):
        assert client.get(path).status_code == 403
    for path in ("/api/v1/translation-settings/import", "/api/v1/translation-settings/ollama/pull"):
        assert client.post(path, json={}).status_code == 403


def test_settings_reads_and_selection_never_start_a_download(monkeypatch):
    from app.ollama_translation import downloads

    monkeypatch.setattr(downloads, "start", lambda _: pytest.fail("Unexpected download"))
    client = TestClient(app, base_url="http://127.0.0.1", headers={"X-YomiMado-Client": "desktop"})
    assert client.get("/api/v1/translation-settings").json()["provider"] == "none"
    assert (
        client.post("/api/v1/translation-settings", json={"provider": "builtin"}).status_code == 422
    )
