"""Inventory local release inputs and copy their available license notices.

This deliberately inventories the whole OCR build environment, including build-only
Python packages, because PyInstaller can freeze optional imports without preserving
their dist-info. An over-inclusive inventory is safer than omitting frozen code.
"""

from __future__ import annotations

import argparse
import ast
import ctypes
import hashlib
import json
import re
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import importlib_metadata as metadata

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "apps/desktop"
TAURI = DESKTOP / "src-tauri"
SITE_PACKAGES = Path(sysconfig.get_paths()["purelib"])
LICENSE_PREFIXES = ("license", "licence", "copying", "notice", "copyright")
UPSTREAM = ROOT / "THIRD_PARTY_LICENSES/upstream"
PYTHON_NOTICE_GROUPS = {
    "loguru": "loguru",
    "sentencepiece": "sentencepiece",
    "sudachipy": "sudachi-rs",
    "tokenizers": "tokenizers",
    "torchsummary": "torchsummary",
}
RUST_NOTICE_GROUPS = {
    "alloc-stdlib": "alloc-stdlib",
    "defmt-parser": "defmt",
    "selectors": "selectors",
    "tauri-plugin": "tauri",
}
PYTHON_LICENSE_OVERRIDES = {
    "opencv-python": "Apache-2.0 AND MIT (static dependency notices included)",
    "manga-ocr": "Apache-2.0",
    "sentencepiece": "Apache-2.0",
    "torchsummary": "MIT",
    "wandb": "MIT",
    "pyinstaller": "GPL-2.0-or-later WITH Bootloader-exception",
}


def command_json(args: list[str], cwd: Path) -> dict:
    result = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._+-]", "_", value)


def license_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    files = []
    for item in directory.iterdir():
        if item.is_file() and item.name.lower().startswith(LICENSE_PREFIXES):
            files.append(item)
        elif item.is_dir() and item.name.lower() == "licenses":
            files.extend(path for path in item.rglob("*") if path.is_file())
    return sorted(files)


def upstream_files(group: str | None) -> tuple[list[Path], Path | None]:
    if not group:
        return [], None
    index = json.loads((UPSTREAM / "sources.json").read_text())
    record = index[group]
    files = []
    for item in record["files"]:
        path = UPSTREAM / item["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Upstream notice checksum mismatch: {path}")
        files.append(path)
    return files, UPSTREAM / group


def copy_asset_notices(notices: Path) -> None:
    index = json.loads((UPSTREAM / "sources.json").read_text())
    for item in index["assets"]["files"]:
        source = UPSTREAM / item["path"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Asset notice checksum mismatch: {source}")
        target = notices / "assets" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def rust_notice_group(name: str) -> str | None:
    if name in ("block2", "dispatch2") or name.startswith("objc2"):
        return "objc2"
    if name.startswith("unic-"):
        return "unic"
    return RUST_NOTICE_GROUPS.get(name)


def add_component(
    components: list[dict],
    notices: Path,
    ecosystem: str,
    name: str,
    version: str,
    license_id: str,
    source: str,
    files: list[Path],
    base: Path,
    authors: list[str] | None = None,
) -> None:
    destination = notices / "licenses" / ecosystem / safe_name(f"{name}-{version}")
    copied = []
    for path in files:
        relative = path.relative_to(base)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(str(target.relative_to(notices)))
    components.append(
        {
            "ecosystem": ecosystem,
            "name": name,
            "version": version,
            "license": license_id or "UNKNOWN",
            "source": source,
            "authors": authors or [],
            "noticeFiles": copied,
        }
    )


def inventory_rust(components: list[dict], notices: Path) -> None:
    metadata = command_json(
        [
            "cargo",
            "metadata",
            "--offline",
            "--locked",
            "--format-version",
            "1",
            "--filter-platform",
            "aarch64-apple-darwin",
        ],
        TAURI,
    )
    for package in metadata["packages"]:
        if package["name"] == "yomimado":
            continue
        directory = Path(package["manifest_path"]).parent
        files = license_files(directory)
        explicit = package.get("license_file")
        if explicit:
            license_path = directory / explicit
            if license_path.is_file() and license_path not in files:
                files.append(license_path)
        base = directory
        if not files:
            files, fallback = upstream_files(rust_notice_group(package["name"]))
            base = fallback or directory
        add_component(
            components,
            notices,
            "rust",
            package["name"],
            package["version"],
            package.get("license") or "",
            package.get("repository") or "",
            files,
            base,
            package.get("authors") or [],
        )


def npm_dependencies(tree: dict) -> dict[str, str]:
    found = {}
    for name, package in tree.get("dependencies", {}).items():
        found[name] = package["version"]
        found.update(npm_dependencies(package))
    return found


def inventory_javascript(components: list[dict], notices: Path) -> None:
    tree = command_json(["npm", "ls", "--omit=dev", "--all", "--json"], DESKTOP)
    for name, version in sorted(npm_dependencies(tree).items()):
        directory = DESKTOP / "node_modules" / name
        package = json.loads((directory / "package.json").read_text())
        homepage = package.get("homepage") or package.get("repository") or ""
        if isinstance(homepage, dict):
            homepage = homepage.get("url", "")
        add_component(
            components,
            notices,
            "javascript",
            name,
            version,
            package.get("license") or "",
            homepage,
            license_files(directory),
            directory,
            [str(package["author"])] if package.get("author") else [],
        )


def packaged_python_distributions() -> tuple[set[str], set[str]]:
    analysis = ROOT / "services/ocr/build/pyinstaller/yomimado-ocr/Analysis-00.toc"
    toc = ast.literal_eval(analysis.read_text())
    module_owners = metadata.packages_distributions()
    distributions = list(metadata.distributions(path=[str(SITE_PACKAGES)]))
    dist_info_owners = {
        Path(item._path).name: item.metadata["Name"] for item in distributions
    }
    included = set()
    unmapped = set()
    for section in (toc[10], toc[14], toc[15], toc[18], toc[19]):
        for entry in section:
            if len(entry) < 2:
                continue
            source = Path(entry[1])
            try:
                top_level = source.relative_to(SITE_PACKAGES).parts[0]
            except (ValueError, IndexError):
                continue
            if top_level.endswith((".dist-info", ".egg-info")):
                owner = dist_info_owners.get(top_level)
                if owner:
                    included.add(owner.lower())
            else:
                owners = module_owners.get(top_level.removesuffix(".py"))
                if owners:
                    included.update(owner.lower() for owner in owners)
                else:
                    unmapped.add(top_level)
    return included, unmapped


def python_license(distribution: metadata.Distribution) -> str:
    expression = distribution.metadata.get("License-Expression")
    if expression:
        return expression
    legacy = distribution.metadata.get("License")
    if (
        legacy
        and "\n" not in legacy
        and len(legacy) <= 120
        and legacy.upper() != "UNKNOWN"
    ):
        return legacy
    classifiers = distribution.metadata.get_all("Classifier", [])
    for marker, label in (
        ("MIT License", "MIT"),
        ("Apache Software License", "Apache-2.0"),
        ("BSD License", "BSD (see notice)"),
    ):
        if any(f"License :: OSI Approved :: {marker}" in item for item in classifiers):
            return label
    return "see notice" if license_files(Path(distribution._path)) else "UNKNOWN"


def inventory_python(components: list[dict], notices: Path) -> set[str]:
    included, unmapped = packaged_python_distributions()
    # The bootloader is linked into the executable, not represented by imports.
    included.add("pyinstaller")
    for distribution in sorted(
        metadata.distributions(path=[str(SITE_PACKAGES)]),
        key=lambda item: (item.metadata["Name"] or "").lower(),
    ):
        name = distribution.metadata["Name"] or "UNKNOWN"
        if name.lower() not in included or name == "yomimado-ocr":
            continue
        directory = Path(distribution._path)  # dist-info path, not import location
        files = license_files(directory)
        base = directory
        if not files:
            files, fallback = upstream_files(PYTHON_NOTICE_GROUPS.get(name.lower()))
            base = fallback or directory
        source = distribution.metadata.get("Home-page") or ""
        if not source:
            for value in distribution.metadata.get_all("Project-URL", []):
                if value.lower().startswith(("source,", "homepage,")):
                    source = value.split(",", 1)[1].strip()
                    break
        add_component(
            components,
            notices,
            "python",
            name,
            distribution.version,
            PYTHON_LICENSE_OVERRIDES.get(name.lower(), python_license(distribution)),
            source,
            files,
            base,
            [distribution.metadata["Author"]]
            if distribution.metadata.get("Author")
            else [],
        )
    return unmapped


def inventory_native(notices: Path) -> None:
    """Record binary provenance separately from wheel-level licence labels.

    A wheel's licence does not necessarily cover its bundled shared libraries.
    Keep the original input digest (before relocation/signing) and avoid leaking
    the builder's absolute paths. These entries require a source/notice review.
    """
    analysis = ROOT / "services/ocr/build/pyinstaller/yomimado-ocr/Analysis-00.toc"
    toc = ast.literal_eval(analysis.read_text())
    binaries = {}
    for section in toc:
        if not isinstance(section, list):
            continue
        for entry in section:
            if not isinstance(entry, tuple) or len(entry) < 3:
                continue
            destination, source, kind = entry[:3]
            if kind not in {"BINARY", "EXTENSION", "DATA"}:
                continue
            path = Path(source)
            if kind == "DATA":
                with path.open("rb") as stream:
                    if stream.read(4) not in {
                        b"\xfe\xed\xfa\xce",
                        b"\xce\xfa\xed\xfe",
                        b"\xfe\xed\xfa\xcf",
                        b"\xcf\xfa\xed\xfe",
                        b"\xca\xfe\xba\xbe",
                        b"\xbe\xba\xfe\xca",
                        b"\xca\xfe\xba\xbf",
                        b"\xbf\xba\xfe\xca",
                    }:
                        continue
            try:
                origin = "site-packages/" + str(path.relative_to(SITE_PACKAGES))
            except ValueError:
                origin = "interpreter/" + path.name
            binaries[destination] = {
                "id": "native:" + destination,
                "path": destination,
                "buildInput": origin,
                "buildInputSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            if path.name.startswith("libavcodec.") and sys.platform == "darwin":
                library = ctypes.CDLL(str(path))
                for field, symbol in (
                    ("reportedLicense", "avcodec_license"),
                    ("reportedConfiguration", "avcodec_configuration"),
                ):
                    function = getattr(library, symbol)
                    function.restype = ctypes.c_char_p
                    binaries[destination][field] = function().decode()
    # Tauri materializes some PyInstaller symlink aliases as regular resource
    # files. Record aliases too, without inventing a second upstream component.
    internal = ROOT / "services/ocr/dist/yomimado-ocr/_internal"
    for path in internal.rglob("*"):
        if not path.is_symlink() or not path.is_file():
            continue
        target = str(path.resolve().relative_to(internal.resolve()))
        if target not in binaries:
            continue
        alias = str(path.relative_to(internal))
        binaries[alias] = {
            **binaries[target],
            "id": "native:" + alias,
            "path": alias,
            "aliasOf": target,
        }
    (notices / "native-libraries.json").write_text(
        json.dumps({"binaries": [binaries[k] for k in sorted(binaries)]}, indent=2)
        + "\n"
    )


def write_index(
    notices: Path, components: list[dict], unmapped: set[str]
) -> list[dict]:
    gaps = [
        item
        for item in components
        if item["license"] == "UNKNOWN"
        or not item["noticeFiles"]
        or "\n" in item["license"]
        or len(item["license"]) > 120
    ]
    lines = [
        "# Third-party software notices",
        "",
        "Generated from the exact local macOS build inputs. The inventory is",
        "conservative: frozen Python dependencies may include optional code.",
        "Model and dictionary credits are in `MODEL_CREDITS.md`.",
        "Native binary provenance is in `native-libraries.json`. Package notices",
        "do not clear nested native licences or corresponding-source obligations;",
        "see `macos-source-review.md` and the release source-delivery gate.",
        "",
        f"Components: {len(components)}. Missing or unresolved notices: {len(gaps)}.",
        "",
        "| Ecosystem | Component | License | License/notice files |",
        "| --- | --- | --- | --- |",
    ]
    for item in components:
        name = f"{item['name']} {item['version']}"
        if item["source"]:
            name = f"[{name}]({item['source']})"
        files = (
            ", ".join(f"[{Path(path).name}]({path})" for path in item["noticeFiles"])
            or "MISSING — review required"
        )
        lines.append(f"| {item['ecosystem']} | {name} | {item['license']} | {files} |")
    if unmapped:
        lines += ["", "Unmapped frozen Python paths: " + ", ".join(sorted(unmapped))]
    (notices / "THIRD_PARTY_SOFTWARE.md").write_text("\n".join(lines) + "\n")
    return gaps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notices", type=Path, help="staging notices directory")
    parser.add_argument(
        "--strict", action="store_true", help="fail for missing licenses/notices"
    )
    args = parser.parse_args()
    notices = args.notices.resolve()
    notices.mkdir(parents=True, exist_ok=True)
    if (UPSTREAM / "sources.json").exists():
        shutil.copy2(
            UPSTREAM / "sources.json", notices / "upstream-notice-sources.json"
        )
        copy_asset_notices(notices)
    components: list[dict] = []
    inventory_rust(components, notices)
    inventory_javascript(components, notices)
    unmapped = inventory_python(components, notices)
    detector = ROOT / "services/ocr/local-models/comic-text-detector"
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=detector, text=True
    ).strip()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=detector):
        raise ValueError("Detector checkout must be clean for release provenance")
    add_component(
        components,
        notices,
        "source",
        "comic-text-detector",
        revision,
        "GPL-3.0 (see LICENSE)",
        "https://github.com/dmMaze/comic-text-detector",
        [detector / "LICENSE"],
        detector,
    )
    inventory_native(notices)
    components.sort(
        key=lambda item: (item["ecosystem"], item["name"].lower(), item["version"])
    )
    (notices / "third-party-manifest.json").write_text(
        json.dumps({"components": components}, ensure_ascii=False, indent=2) + "\n"
    )
    gaps = write_index(notices, components, unmapped)
    print(
        f"Inventoried {len(components)} third-party packages; {len(gaps)} missing package notices."
    )
    native_count = len(
        json.loads((notices / "native-libraries.json").read_text())["binaries"]
    )
    print(
        f"Native binary inputs: {native_count}; separate source/licence review required."
    )
    for item in gaps:
        print(
            f"  {item['ecosystem']}: {item['name']} {item['version']} — {item['license']}"
        )
    if unmapped:
        print("Unmapped frozen Python paths: " + ", ".join(sorted(unmapped)))
    return 1 if args.strict and (gaps or unmapped) else 0


if __name__ == "__main__":
    sys.exit(main())
