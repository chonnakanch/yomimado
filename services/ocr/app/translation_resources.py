"""Explicit, checksum-verified installation of an optional local model component."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
import threading
import urllib.request
import zipfile
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError
from urllib.parse import urlparse

SHA = re.compile(r"[0-9a-f]{64}")
MAX_BYTES = 1_500_000_000


@contextmanager
def download_lock(root: Path):
    """OS-released lock permits safe cleanup after a service is interrupted."""
    with (root / "download.lock").open("a+b") as lock:
        lock.write(b"0")
        lock.flush()
        lock.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def read_manifest(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    files = value["files"]
    if (
        value.get("schemaVersion") != 1
        or not SHA.fullmatch(value.get("id", ""))
        or value.get("backend") not in {"torch", "onnx"}
        or not isinstance(files, dict)
        or not files
        or not SHA.fullmatch(value["archive"].get("sha256", ""))
        or not 0 < value["archive"]["bytes"] <= MAX_BYTES
    ):
        raise ValueError("Invalid translation component manifest")
    for name, pin in files.items():
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or "\\" in name
            or relative.as_posix() != name
            or not relative.parts
            or relative.parts[0] not in {"model", "onnx", "notices"}
            or not SHA.fullmatch(pin.get("sha256", ""))
            or not 0 < pin["bytes"] <= MAX_BYTES
        ):
            raise ValueError("Unsafe translation component member")
    identity = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    if identity != value["id"] or sum(p["bytes"] for p in files.values()) > MAX_BYTES:
        raise ValueError("Translation component identity differs")
    url = urlparse(value["archive"]["url"])
    if (
        url.scheme != "https"
        or url.hostname != "github.com"
        or url.username
        or url.password
        or url.port not in (None, 443)
        or url.query
        or url.fragment
        or not url.path.startswith("/chonnakanch/yomimado/releases/download/")
    ):
        raise ValueError("Unsupported translation component download source")
    return value


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        url = urlparse(newurl)
        if (
            url.scheme != "https"
            or url.hostname
            not in {
                "github.com",
                "release-assets.githubusercontent.com",
                "objects.githubusercontent.com",
            }
            or url.username
            or url.password
            or url.port not in (None, 443)
        ):
            raise ValueError("Unexpected translation download redirect")
        return super().redirect_request(request, fp, code, message, headers, newurl)


class TranslationResources:
    def __init__(self, manifest: Path | None, root: Path):
        self.manifest = read_manifest(manifest) if manifest else None
        self.root = root
        self.lock = threading.Lock()
        self.downloading = False
        self.received = 0
        self.error: str | None = None
        self.verified = False

    @property
    def directory(self) -> Path:
        if not self.manifest:
            raise FileNotFoundError(
                "Translation is not configured. Set YOMIMADO_TRANSLATION_MODEL for a source service, or download it in Settings → Reading in a packaged app"
            )
        return self.root / self.manifest["id"]

    def model_path(self) -> Path:
        directory = self.directory
        if not self.verified:
            if not (directory / "installed.json").is_file():
                raise FileNotFoundError("Download local translation in Settings → Reading first")
            self.verify(directory)
            self.verified = True
        return directory / "model"

    def verify(self, directory: Path) -> None:
        present = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
        if present - {"installed.json"} != set(self.manifest["files"]):
            raise ValueError("Translation component membership differs")
        for name, pin in self.manifest["files"].items():
            path = directory / name
            if (
                path.is_symlink()
                or not path.is_file()
                or path.stat().st_size != pin["bytes"]
                or digest(path) != pin["sha256"]
                or directory.is_symlink()
                or not path.resolve().is_relative_to(directory.resolve())
            ):
                raise ValueError("Translation component checksum differs: " + name)

    def status(self) -> dict:
        with self.lock:
            state = "unavailable" if not self.manifest else "notInstalled"
            if self.manifest and not self.downloading:
                try:
                    self.model_path()
                    state = "ready"
                    self.error = None
                except FileNotFoundError:
                    pass
                except (OSError, ValueError) as error:
                    self.error = str(error)
            if self.error:
                state = "error"
            if self.downloading:
                state = "downloading"
            return {
                "state": state,
                "receivedBytes": self.received,
                "downloadBytes": self.manifest["archive"]["bytes"] if self.manifest else 0,
                "error": self.error,
            }

    def start(self) -> dict:
        with self.lock:
            if not self.manifest:
                raise RuntimeError("Translation download is not configured in this build")
            if not self.downloading:
                self.downloading, self.error, self.received = True, None, 0
                threading.Thread(target=self._download, daemon=True).start()
        return self.status()

    def _download(self):
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with download_lock(self.root):
                # Only reserved model-staging paths, never saved learning data.
                for prefix in (".translation-", ".replaced-"):
                    for path in self.root.glob(prefix + "*"):
                        if path.is_symlink():
                            path.unlink()
                        elif path.is_dir():
                            shutil.rmtree(path)
                with tempfile.TemporaryDirectory(
                    prefix=".translation-", dir=self.root
                ) as temporary:
                    temporary = Path(temporary)
                    archive = temporary / "download.zip"
                    pin = self.manifest["archive"]
                    opener = urllib.request.build_opener(SafeRedirect())
                    with (
                        opener.open(pin["url"], timeout=60) as response,
                        archive.open("wb") as output,
                    ):
                        while chunk := response.read(1024 * 1024):
                            with self.lock:
                                self.received += len(chunk)
                                if self.received > pin["bytes"]:
                                    raise ValueError(
                                        "Translation download exceeds its expected size"
                                    )
                            output.write(chunk)
                    self.install_archive(archive, temporary / "staged")
        except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
            logging.getLogger(__name__).warning("Optional translation download failed: %s", error)
            with self.lock:
                if isinstance(error, HTTPError) and error.code == 404:
                    self.error = "This model download is not available for your app version. Update YomiMado or try again later."
                elif isinstance(error, (ValueError, zipfile.BadZipFile)):
                    self.error = "The downloaded model failed verification. Please retry."
                else:
                    self.error = "Download failed. Check your connection and available disk space, then retry."
        finally:
            with self.lock:
                self.downloading = False

    def install_archive(self, archive: Path, staged: Path) -> None:
        pin = self.manifest["archive"]
        if archive.stat().st_size != pin["bytes"] or digest(archive) != pin["sha256"]:
            raise ValueError("Translation archive checksum differs")
        self.root.mkdir(parents=True, exist_ok=True)
        staged.mkdir()
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist()
            if len(members) != len(self.manifest["files"]) or {m.filename for m in members} != set(
                self.manifest["files"]
            ):
                raise ValueError("Unexpected translation archive membership")
            for item in members:
                expected = self.manifest["files"][item.filename]
                if (
                    item.is_dir()
                    or item.file_size != expected["bytes"]
                    or (item.external_attr >> 16) & 0o170000 == 0o120000
                ):
                    raise ValueError("Unsafe translation archive member")
                target = staged / item.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(item) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
        self.verify(staged)
        (staged / "installed.json").write_text(json.dumps({"id": self.manifest["id"]}))
        # An interrupted download never becomes the live model. Retry can repair
        # this managed model directory only after the replacement is verified.
        if self.directory.exists():
            try:
                self.verify(self.directory)
            except ValueError:
                with tempfile.TemporaryDirectory(prefix=".replaced-", dir=self.root) as temporary:
                    previous = Path(temporary) / "model"
                    self.directory.rename(previous)
                    try:
                        staged.rename(self.directory)
                    except OSError:
                        previous.rename(self.directory)
                        raise
        else:
            staged.rename(self.directory)
        self.verified = True


@lru_cache(maxsize=1)
def resources() -> TranslationResources:
    value = os.environ.get("YOMIMADO_TRANSLATION_MANIFEST")
    root = os.environ.get("YOMIMADO_TRANSLATION_RESOURCES")
    return TranslationResources(
        Path(value) if value else None,
        Path(root) if root else Path.home() / ".cache/yomimado/models/translation",
    )


def local_model_path() -> Path:
    override = os.environ.get("YOMIMADO_TRANSLATION_MODEL")
    if override:
        path = Path(override).expanduser().resolve()
        if not path.is_dir():
            raise FileNotFoundError("Translation model directory does not exist: " + str(path))
        return path
    return resources().model_path()
