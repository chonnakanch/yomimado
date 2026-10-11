"""Readiness belongs to a successfully bound service, never an unrelated listener."""

import asyncio
import json
import os

import pytest
import uvicorn

from windows_packaged_main import WindowsServer


def test_ready_file_is_atomic_and_bound_to_process(tmp_path, monkeypatch):
    path = tmp_path / "ready.json"
    monkeypatch.setenv("YOMIMADO_READY_FILE", str(path))
    monkeypatch.setenv("YOMIMADO_SERVICE_INSTANCE", "current-instance")

    async def bound(server, sockets=None):
        server.started = True

    monkeypatch.setattr(uvicorn.Server, "startup", bound)
    server = WindowsServer(uvicorn.Config("app.main:app", port=8766))
    asyncio.run(server.startup())
    assert json.loads(path.read_text()) == {
        "pid": os.getpid(),
        "port": 8766,
        "instanceId": "current-instance",
    }
    assert not path.with_suffix(".tmp").exists()


def test_unsuccessful_bind_never_claims_readiness(tmp_path, monkeypatch):
    path = tmp_path / "ready.json"
    monkeypatch.setenv("YOMIMADO_READY_FILE", str(path))

    async def failed(server, sockets=None):
        server.started = False

    monkeypatch.setattr(uvicorn.Server, "startup", failed)
    server = WindowsServer(uvicorn.Config("app.main:app", port=8766))
    asyncio.run(server.startup())
    assert not path.exists()


def test_port_conflict_does_not_write_readiness(tmp_path, monkeypatch):
    path = tmp_path / "ready.json"
    monkeypatch.setenv("YOMIMADO_READY_FILE", str(path))

    async def occupied(server, sockets=None):
        raise SystemExit(1)

    monkeypatch.setattr(uvicorn.Server, "startup", occupied)
    server = WindowsServer(uvicorn.Config("app.main:app", port=8766))
    with pytest.raises(SystemExit):
        asyncio.run(server.startup())
    assert not path.exists()
