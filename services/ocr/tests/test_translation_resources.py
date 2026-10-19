import hashlib
import io
import json
import threading
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.api import translation as api
from app.main import app
from app.translation_resources import TranslationResources, digest, read_manifest


def fixture(tmp_path, members=None):
    members = members or {"model/config.json": b"{}", "model/pytorch_model.bin": b"model"}
    archive = tmp_path / "model.zip"
    with zipfile.ZipFile(archive, "w") as output:
        for name, data in members.items():
            output.writestr(name, data)
    files = {
        name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        for name, data in members.items()
    }
    manifest = {
        "schemaVersion": 1,
        "backend": "torch",
        "id": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
        "files": files,
        "archive": {
            "url": "https://github.com/chonnakanch/yomimado/releases/download/v1/model.zip",
            "bytes": archive.stat().st_size,
            "sha256": digest(archive),
        },
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return TranslationResources(path, tmp_path / "installed"), archive, path


def test_installation_is_atomic_verified_and_survives_restart(tmp_path):
    manager, archive, path = fixture(tmp_path)
    assert manager.status()["state"] == "notInstalled"
    manager.install_archive(archive, tmp_path / "staged")
    assert manager.status()["state"] == "ready"
    restarted = TranslationResources(path, manager.root)
    assert restarted.model_path().joinpath("pytorch_model.bin").read_bytes() == b"model"
    restarted.model_path().joinpath("pytorch_model.bin").write_bytes(b"corrupt")
    assert TranslationResources(path, manager.root).status()["state"] == "error"
    repaired = TranslationResources(path, manager.root)
    repaired.install_archive(archive, tmp_path / "repair")
    assert repaired.status()["state"] == "ready"


def test_failed_archive_never_becomes_a_live_model(tmp_path):
    manager, archive, _ = fixture(tmp_path)
    archive.write_bytes(b"truncated download")
    with pytest.raises(ValueError, match="checksum"):
        manager.install_archive(archive, tmp_path / "staged")
    assert not manager.directory.exists()
    assert manager.status()["state"] == "notInstalled"


@pytest.mark.parametrize(
    "name", ["../model.bin", "/absolute", "model/../../escape", "model\\escape"]
)
def test_manifest_rejects_unsafe_archive_paths(tmp_path, name):
    with pytest.raises(ValueError, match="Unsafe"):
        fixture(tmp_path, {name: b"bad"})


def test_archive_cannot_add_extra_files_even_with_a_new_archive_hash(tmp_path):
    manager, archive, _ = fixture(tmp_path)
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("model/unexpected.py", b"bad")
    manager.manifest["archive"].update(sha256=digest(archive), bytes=archive.stat().st_size)
    with pytest.raises(ValueError, match="membership"):
        manager.install_archive(archive, tmp_path / "staged")
    assert not manager.directory.exists()


def test_only_the_explicit_install_api_starts_a_download(tmp_path, monkeypatch):
    manager, archive, _ = fixture(tmp_path)
    orphan = manager.root / ".translation-interrupted"
    orphan.mkdir(parents=True)
    (orphan / "partial.zip").write_bytes(b"interrupted download")
    monkeypatch.setattr(api, "resources", lambda: manager)
    entered, proceed, finished = threading.Event(), threading.Event(), threading.Event()
    calls = []

    class Opener:
        def open(self, url, timeout):
            calls.append(url)
            entered.set()
            assert proceed.wait(5)
            return io.BytesIO(archive.read_bytes())

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: Opener())
    original = manager._download

    def download():
        try:
            original()
        finally:
            finished.set()

    monkeypatch.setattr(manager, "_download", download)
    client = TestClient(app, base_url="http://127.0.0.1", headers={"X-YomiMado-Client": "desktop"})
    assert client.get("/api/v1/translation-model").json()["state"] == "notInstalled"
    assert calls == []
    assert client.post("/api/v1/translation-model/install").json()["state"] == "downloading"
    assert entered.wait(5)
    client.post("/api/v1/translation-model/install")
    assert len(calls) == 1
    proceed.set()
    assert finished.wait(5)
    assert client.get("/api/v1/translation-model").json()["state"] == "ready"
    assert manager.received == archive.stat().st_size
    assert not orphan.exists()


def test_download_api_requires_the_desktop_header_before_accessing_resources(monkeypatch):
    monkeypatch.setattr(api, "resources", lambda: pytest.fail("Resources must not be accessed"))
    client = TestClient(app, base_url="http://127.0.0.1")
    assert client.post("/api/v1/translation-model/install").status_code == 403


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/chonnakanch/yomimado/releases/download/v1/a.zip",
        "https://127.0.0.1/a",
        "https://github.com/other/repo/releases/download/a",
    ],
)
def test_manifest_cannot_redirect_downloads_to_arbitrary_servers(tmp_path, url):
    _, _, path = fixture(tmp_path)
    value = json.loads(path.read_text())
    value["archive"]["url"] = url
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="download source"):
        read_manifest(path)
