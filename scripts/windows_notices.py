"""Collect Windows-target notices and exact locked desktop source archives.

This is evidence preparation, not approval of embedded native libraries.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from urllib.request import urlopen

import tomllib
from windows_release import BUILD, RESOURCES, ROOT, digest, fetch, read_json, write_json

DESKTOP = ROOT / "apps/desktop"
UPSTREAM = ROOT / "THIRD_PARTY_LICENSES/upstream"
PREFIXES = ("license", "licence", "copying", "notice", "copyright")


def canonical_source_tar(original: Path, destination: Path) -> None:
    """Keep all paths, modes and source bytes; remove variable Gitiles metadata."""
    with tarfile.open(original) as source:
        members = sorted(source.getmembers(), key=lambda member: member.name)
        seen = set()
        total = 0
        for member in members:
            path = PurePosixPath(member.name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or path.as_posix() != member.name
                or "\\" in member.name
                or ":" in member.name
                or member.name in seen
                or not (member.isfile() or member.isdir())
                or member.mode & ~0o777
                not in (0, 0o100000 if member.isfile() else 0o040000)
            ):
                raise ValueError("Unsafe or duplicate preferred-source member")
            seen.add(member.name)
            total += member.size
        if not members or total > 128 * 1024 * 1024:
            raise ValueError("Unexpected preferred-source archive size")
        with tarfile.open(destination, "w", format=tarfile.PAX_FORMAT) as target:
            for member in members:
                normalized = tarfile.TarInfo(member.name)
                normalized.type = member.type
                normalized.mode = member.mode & 0o777
                normalized.size = member.size if member.isfile() else 0
                target.addfile(
                    normalized, source.extractfile(member) if member.isfile() else None
                )


def native_notice_source(entry: dict, destination: Path) -> None:
    if entry.get("archiveNormalization") != "gitiles-tar-v1":
        fetch(entry, destination)
        return
    url = urlsplit(entry["url"])
    revision = entry["revision"]
    if (
        url.scheme != "https"
        or url.hostname not in {"chromium.googlesource.com", "aomedia.googlesource.com"}
        or len(revision) != 40
        or any(character not in "0123456789abcdef" for character in revision)
        or not url.path.endswith("/+archive/" + revision + ".tar.gz")
        or url.query
        or url.fragment
        or url.netloc != url.hostname
    ):
        raise ValueError("Unpinned Gitiles preferred-source URL")
    if destination.is_file() and digest(destination) == entry["sha256"]:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    downloaded = destination.with_name(destination.name + ".download")
    normalized = destination.with_name(destination.name + ".canonical")
    try:
        with (
            urlopen(entry["url"], timeout=120) as response,
            downloaded.open("wb") as out,
        ):
            shutil.copyfileobj(response, out)
        canonical_source_tar(downloaded, normalized)
        if digest(normalized) != entry["sha256"]:
            raise ValueError("Preferred-source tree checksum changed")
        normalized.replace(destination)
    finally:
        downloaded.unlink(missing_ok=True)
        normalized.unlink(missing_ok=True)


def license_files(directory: Path) -> list[Path]:
    files = []
    for path in directory.iterdir():
        if path.is_file() and path.name.lower().startswith(PREFIXES):
            files.append(path)
        elif path.is_dir() and path.name.lower() in ("licenses", "licences"):
            files.extend(p for p in path.rglob("*") if p.is_file())
    return sorted(files)


def supplement(group: str, destination: Path) -> list[str]:
    files = []
    for entry in read_json(UPSTREAM / "sources.json")[group]["files"]:
        original = UPSTREAM / entry["path"]
        if digest(original) != entry["sha256"]:
            raise ValueError("Upstream notice hash differs: " + str(original))
        target = destination / original.relative_to(UPSTREAM / group)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
        files.append(str(target))
    return files


def notices(directory: Path, destination: Path, extra=None) -> list[str]:
    files = license_files(directory)
    if extra and (directory / extra).is_file() and directory / extra not in files:
        files.append(directory / extra)
    copied = []
    for original in files:
        target = destination / original.relative_to(directory)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
        copied.append(str(target))
    return copied


def tar_notices(entry: dict, archive: Path, destination: Path) -> list[str]:
    """Preserve original vendor texts; reject changed, linked or escaping inputs."""
    if digest(archive) != entry["sha256"]:
        raise ValueError("Native source archive hash differs")
    selected = entry["licenseFiles"]
    if not selected:
        raise ValueError("Native source has no pinned notices")
    verified = {}
    with tarfile.open(archive) as source:
        for name, sha in selected.items():
            relative = PurePosixPath(name)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or relative.as_posix() != name
                or "\\" in name
                or ":" in name
            ):
                raise ValueError("Unsafe native notice path")
            member = source.getmember(name)
            if not member.isfile():
                raise ValueError("Native notice is not a regular source file")
            content = source.extractfile(member).read()
            if hashlib.sha256(content).hexdigest() != sha:
                raise ValueError("Native source notice hash differs")
            verified[name] = content
    copied = []
    for name, content in verified.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        copied.append(str(target))
    return copied


def rust_components(output: Path) -> list[dict]:
    data = json.loads(
        subprocess.check_output(
            [
                "cargo",
                "metadata",
                "--locked",
                "--format-version",
                "1",
                "--filter-platform",
                "x86_64-pc-windows-msvc",
            ],
            cwd=DESKTOP / "src-tauri",
            text=True,
            encoding="utf-8",
        )
    )
    included = {node["id"] for node in data["resolve"]["nodes"]}
    lock = tomllib.loads((DESKTOP / "src-tauri/Cargo.lock").read_text(encoding="utf-8"))
    hashes = {(p["name"], p["version"]): p.get("checksum") for p in lock["package"]}
    vendor_licenses = {
        (crate["name"], crate["version"]): (vendor, crate)
        for vendor in read_json(ROOT / "services/ocr/windows-inputs.json")[
            "desktopVendorInputs"
        ]
        for crate in vendor.get("coveredCrates", [])
    }
    result = []
    for package in data["packages"]:
        if package["id"] not in included or package["name"] == "yomimado":
            continue
        name, version = package["name"], package["version"]
        key = name + "-" + version
        directory = Path(package["manifest_path"]).parent
        copied = notices(
            directory, output / "licenses/rust" / key, package.get("license_file")
        )
        if not copied:
            group = (
                "unic"
                if name.startswith("unic-")
                else {
                    "alloc-stdlib": "alloc-stdlib",
                    "defmt-parser": "defmt",
                    "selectors": "selectors",
                    "tauri-plugin": "tauri",
                }.get(name)
            )
            if group:
                copied = supplement(group, output / "licenses/rust" / key)
            elif (name, version) in vendor_licenses:
                vendor, crate = vendor_licenses[(name, version)]
                vcs = read_json(directory / ".cargo_vcs_info.json")
                license_path = (
                    output / "licenses/windows-vendors" / vendor["name"] / "LICENSE.txt"
                )
                if (
                    vcs["git"]["sha1"] != crate["revision"]
                    or digest(license_path) != vendor["sha256"]
                ):
                    raise ValueError("Windows crate upstream licence evidence differs")
                copied = [str(license_path)]
        sha = hashes[(name, version)]
        if not sha or not package["source"].startswith("registry+"):
            raise ValueError("Unpinned/non-registry Windows crate: " + key)
        source = BUILD / "sources/rust" / (key + ".crate")
        fetch(
            {
                "url": f"https://static.crates.io/crates/{name}/{key}.crate",
                "sha256": sha,
            },
            source,
        )
        result.append(
            {
                "ecosystem": "rust",
                "name": name,
                "version": version,
                "license": package.get("license"),
                "noticeFiles": copied,
                "sourceArchive": str(source.relative_to(BUILD)),
                "sourceSha256": sha,
                "review": "pending",
            }
        )
    return result


def npm_source(entry: dict, destination: Path) -> str:
    integrity = entry["integrity"]
    algorithm, encoded = integrity.split("-", 1)
    if algorithm != "sha512" or not entry["resolved"].startswith(
        "https://registry.npmjs.org/"
    ):
        raise ValueError("Unsupported/unpinned npm source")
    expected = base64.b64decode(encoded, validate=True).hex()
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".download")
        try:
            with (
                urlopen(entry["resolved"], timeout=120) as response,
                temporary.open("wb") as out,
            ):
                shutil.copyfileobj(response, out)
            with temporary.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha512").hexdigest()
            if actual != expected:
                raise ValueError("npm original source integrity differs")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    with destination.open("rb") as stream:
        if hashlib.file_digest(stream, "sha512").hexdigest() != expected:
            raise ValueError("npm original source integrity differs")
    return digest(destination)


def javascript_components(output: Path) -> list[dict]:
    result = []
    lock = read_json(DESKTOP / "package-lock.json")
    for relative, entry in lock["packages"].items():
        directory = DESKTOP / relative
        if not relative or not directory.is_dir():
            continue  # Optional foreign-platform packages are not installed inputs.
        package = read_json(directory / "package.json")
        name, version = package["name"], package["version"]
        if version != entry["version"]:
            raise ValueError("Installed npm version differs from lock")
        key = name.replace("/", "_") + "-" + version
        source = BUILD / "sources/javascript" / (key + ".tgz")
        sha = npm_source(entry, source)
        result.append(
            {
                "ecosystem": "javascript",
                "name": name,
                "version": version,
                "license": package.get("license"),
                "buildOnly": bool(entry.get("dev")),
                "noticeFiles": notices(directory, output / "licenses/javascript" / key),
                "sourceArchive": str(source.relative_to(BUILD)),
                "sourceSha256": sha,
                "review": "pending",
            }
        )
    return result


def python_native_supplement(
    entry: dict, package: dict, original: Path, notice: Path, destination: Path
) -> None:
    """Bind a full supplemental notice to the exact embedded source bytes."""
    if (
        package["name"] != entry["package"]
        or package["version"] != entry["version"]
        or digest(original) != package["source"]["sha256"]
        or digest(notice) != entry["noticeSha256"]
    ):
        raise ValueError("Native supplemental notice/input identity differs")
    with tarfile.open(original) as source:
        member = source.getmember(entry["sourceMember"])
        if (
            not member.isfile()
            or hashlib.sha256(source.extractfile(member).read()).hexdigest()
            != entry["sourceMemberSha256"]
        ):
            raise ValueError("Native supplemental source member differs")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(notice, destination)


def collect() -> None:
    output = RESOURCES / "notices"
    output.mkdir(parents=True, exist_ok=True)
    # These verified texts resolve missing wheel texts; they confer no Windows approval.
    for package, group in {
        "sudachipy": "sudachi-rs",
        "numpy": "lgpl-2.1",
        "loguru": "loguru",
        "sentencepiece": "sentencepiece",
        "tokenizers": "tokenizers",
        "torchsummary": "torchsummary",
    }.items():
        supplement(group, output / "licenses/python-supplement" / package)
    pins = read_json(ROOT / "services/ocr/windows-inputs.json")
    for entry in pins.get("nativeNoticeSupplements", []):
        package = next(p for p in pins["packages"] if p["name"] == entry["package"])
        python_native_supplement(
            entry,
            package,
            BUILD / "sources" / package["source"]["filename"],
            ROOT / entry["notice"],
            output / "licenses/windows-python-supplement" / Path(entry["notice"]).name,
        )
    native_inputs = read_json(ROOT / "services/ocr/windows-inputs.json")[
        "nativeNoticeInputs"
    ]
    for entry in native_inputs:
        tar_notices(
            entry,
            BUILD / "sources/native-notices" / entry["filename"],
            output / "licenses/windows-python-vendors" / entry["name"],
        )
    vendor_inputs = read_json(ROOT / "services/ocr/windows-inputs.json")[
        "desktopVendorInputs"
    ]
    for entry in vendor_inputs:
        archive = BUILD / "sources/vendors" / entry["filename"]
        if digest(archive) != entry["sha256"]:
            raise ValueError("Desktop vendor input hash differs")
        destination = output / "licenses/windows-vendors" / entry["name"]
        destination.mkdir(parents=True, exist_ok=True)
        if archive.suffix in (".nupkg", ".whl"):
            with zipfile.ZipFile(archive) as source:
                selected = entry.get("noticeFiles", ["LICENSE.txt", "NOTICE.txt"])
                if not set(selected).issubset(entry["fileHashes"]):
                    raise ValueError("Vendor notice is not checksum pinned")
                for name, sha in entry["fileHashes"].items():
                    content = source.read(name)
                    if hashlib.sha256(content).hexdigest() != sha:
                        raise ValueError("SDK vendor file hash differs")
                    if name in selected:
                        target = destination / Path(name).name
                        if target.exists() and target.read_bytes() != content:
                            raise ValueError("Colliding vendor notice filenames")
                        target.write_bytes(content)
        else:
            shutil.copy2(archive, destination / "LICENSE.txt")
    installer_sources = read_json(ROOT / "services/ocr/windows-inputs.json")[
        "installerSourceInputs"
    ]
    for entry in installer_sources:
        archive = BUILD / "sources/installer" / entry["filename"]
        if digest(archive) != entry["sha256"]:
            raise ValueError("Installer source archive hash differs")
        destination = output / "licenses/windows-installer" / entry["name"]
        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as source:
            for name, sha in entry["licenseFiles"].items():
                member = source.getmember(name)
                if not member.isfile():
                    raise ValueError("Installer notice is not a regular source file")
                content = source.extractfile(member).read()
                if hashlib.sha256(content).hexdigest() != sha:
                    raise ValueError("Installer source notice hash differs")
                (destination / Path(name).name).write_bytes(content)
    record = {
        "target": "x86_64-pc-windows-msvc",
        "components": rust_components(output) + javascript_components(output),
        "publicDistributionApproved": False,
        "desktopVendorInputs": vendor_inputs,
        "installerSourceInputs": installer_sources,
        "nativeNoticeInputs": native_inputs,
        "nativeNoticeSupplements": pins.get("nativeNoticeSupplements", []),
    }
    loader = output / "source-webview-loader/windows-webview-loader.json"
    if loader.is_file():
        record["sourceWebViewLoader"] = read_json(loader)
        record["desktopVendorInputs"] = [dict(entry) for entry in vendor_inputs]
        for entry in record["desktopVendorInputs"]:
            if entry["name"] == "Microsoft.Web.WebView2":
                entry["selectedForLinking"] = False
                entry["usedAs"] = (
                    "Public headers and notices; SDK loader archive replaced by retained source-built library"
                )
    # Store portable relative notice paths, never assume Mac target membership.
    for component in record["components"]:
        component["noticeFiles"] = [
            Path(p).relative_to(output).as_posix() for p in component["noticeFiles"]
        ]
    write_json(output / "windows-desktop-sources.json", record)
    write_json(BUILD / "windows-desktop-sources.json", record)


def installer_inputs(installed: Path, installer: Path) -> dict:
    from windows_release import native_files, pe_info, verify_desktop_gui

    files = []
    for path in native_files(installed):
        if "ocr" not in path.relative_to(installed).parts:
            files.append(
                {
                    "path": path.relative_to(installed).as_posix(),
                    "sha256": digest(path),
                    **pe_info(path),
                    "review": "pending",
                }
            )
    # NSIS uses a 32-bit setup/plugin host even when the application payload is x64.
    cache = Path(os.environ["LOCALAPPDATA"]) / "tauri/NSIS"
    tools = []
    if not cache.is_dir():
        raise ValueError(
            "Missing actual NSIS tool cache; cannot inventory installer inputs"
        )
    for path in sorted(cache.rglob("*")):
        if path.is_file():
            with path.open("rb") as stream:
                pe = stream.read(2) == b"MZ"
            if (
                pe
                or path.name.lower().startswith(PREFIXES)
                or path.suffix.lower() in (".nsh", ".nsi")
            ):
                tools.append(
                    {
                        "path": path.relative_to(cache).as_posix(),
                        "sha256": digest(path),
                        **(pe_info(path) if pe else {}),
                        "review": "pending",
                    }
                )
    record = {
        "desktopBinaries": files,
        "installer": {"sha256": digest(installer), **pe_info(installer)},
        "nsisInputs": tools,
        "sourceReview": "pending",
        "publicDistributionApproved": False,
    }
    if (
        installed / "ocr/notices/source-webview-loader/windows-webview-loader.json"
    ).is_file():
        from windows_webview_runtime import verify

        record["sourceWebViewLoader"] = verify(installed / "yomimado.exe")
    write_json(BUILD / "windows-installer-inputs.json", record)
    verify_desktop_gui(installed / "yomimado.exe")
    # Prove desktop loading separately from the frozen Python search path.
    # An NSIS uninstaller is a 32-bit host; the actual app/DLL payload is x64.
    desktop = [entry for entry in files if entry["path"].lower() != "uninstall.exe"]
    bundled = {Path(entry["path"]).name.lower() for entry in desktop}
    system = Path(os.environ["SystemRoot"]) / "System32"
    for entry in desktop:
        if entry["machine"] != "0x8664":
            raise ValueError("Desktop native payload is not x64: " + entry["path"])
        for name in entry["imports"]:
            if name in bundled or name.startswith(("api-ms-win-", "ext-ms-win-")):
                continue
            if (
                name != "msvcp_win.dll"
                and name.startswith(("vcruntime", "msvcp", "vcomp", "concrt"))
                or not (system / name).is_file()
            ):
                raise ValueError("Missing desktop app-local native dependency: " + name)
    return record


if __name__ == "__main__":
    collect()
