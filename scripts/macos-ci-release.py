"""Versioned main-branch releases using the already reviewed frozen runtime.

Dependency or OCR changes require a newly reviewed seed, rather than silently
reusing old code or extending the maintainer's licence approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tomllib
from pathlib import Path

SEED_REVISION = "f1b4fbaa8980ff0df0a1abf6f5a93df058f4678e"
ROOT = Path(__file__).resolve().parent.parent

# Technical review: docs/macos-runtime-reuse-0.4.0.md. These exact frontend
# data/notice/recipe bytes are independent of the reused frozen service. Do not
# allow the directory or repin the runtime: later data/terms edits need review.
FRONTEND_DATA_HASHES = {
    "THIRD_PARTY_LICENSES/ASSET_NOTICES.md": "bb6ba2e8235245b34cfe07e0684493acab959b9ad79d0f168ff217fab3709203",
    "THIRD_PARTY_LICENSES/README.md": "3f38408d212750403c71944dc6b00bec18fc0f101e8433abd84a3f188cd05ace",
    "THIRD_PARTY_LICENSES/jlpt/LICENSE.txt": "7abe19ec9bb73b36141b999b861d24ad855e808bafe0f81e84cce28556f6c297",
    "THIRD_PARTY_LICENSES/jlpt/README.md": "5cad01beb4c9dcf93ac09ddc56063fe54602fed0e62a920637c3ebb39dcbaa4c",
    "THIRD_PARTY_LICENSES/jlpt/UPSTREAM_README.md": "4efd40eecf18c01a61ca54d4c1731daa0756a384b0f4ade551b43914a087869a",
    "THIRD_PARTY_LICENSES/jlpt/source/index.json": "1eb3c86c7d19e6314a8061b2f6a7478e99d7e65cafcac16c071d2dcb71da3513",
    "THIRD_PARTY_LICENSES/jlpt/source/term_meta_bank_1.json": "80698c74b0d4efe476db35626b60324007f66d5ca32c0178bf3f9456a0290abf",
    "THIRD_PARTY_LICENSES/jlpt/source/term_meta_bank_2.json": "c58e20a6fc2dececf6a5e42bd1163212615ef79deec85e77c6f7c7deb4d4cc7e",
    "THIRD_PARTY_LICENSES/jlpt/source/term_meta_bank_3.json": "baeee2da06c41ea973cb54a6118834682b33857128f7d97577f21cbaaae7c51b",
    "THIRD_PARTY_LICENSES/jlpt/source/term_meta_bank_4.json": "844590546217e084f8244f3cf9e6eb6054f5f7a370857bf5917fe19d4d83d7a8",
    "THIRD_PARTY_LICENSES/jlpt/source/term_meta_bank_5.json": "a169779f5b8e4dbf4aaa86c367e2b0e24721b5d247c8e0c5b37b18189bc1be83",
    "THIRD_PARTY_LICENSES/jlpt/sources.json": "e13ab93e53b020e0a9a210f1e60b1fea08606658d942e34001f5df2dc2ac3141",
    "scripts/prepare_jlpt.py": "549804cc65d0f7fdca4539d933081f55e91f4afb609eafb9ff648ddd41993535",
    "apps/desktop/src/features/jlpt/vocabulary.json": "2c280b1168ab93458c365f35c77c0def20345c2d4daa94a9d53310d4f94e50a7",
    "apps/desktop/src/features/jlpt/LICENSE.txt": "7abe19ec9bb73b36141b999b861d24ad855e808bafe0f81e84cce28556f6c297",
}


def committed_bytes(path: str, root: Path = ROOT) -> bytes:
    return subprocess.check_output(["git", "show", f"HEAD:{path}"], cwd=root)


def verify_frontend_data(root: Path = ROOT) -> dict:
    for path, checksum in FRONTEND_DATA_HASHES.items():
        if hashlib.sha256(committed_bytes(path, root)).hexdigest() != checksum:
            raise ValueError("Frontend data/source review hash changed: " + path)
    return {
        "id": "frontend:jlpt-vocabulary",
        "license": "CC-BY-SA-4.0",
        "upstreamRevision": "b062d4e38c4bdd0950ae1d4ec55f04b176182e03",
        "review": "docs/macos-runtime-reuse-0.4.0.md",
        "noticeDirectory": "frontend-jlpt",
        "files": dict(FRONTEND_DATA_HASHES),
    }


def git(*args: str, root: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def is_prerelease(app_version: str) -> bool:
    number = r"(?:0|[1-9][0-9]*)"
    if not re.fullmatch(
        rf"{number}\.{number}\.{number}(?:-(?:alpha|beta|rc)\.{number})?", app_version
    ):
        raise ValueError("Expected a release version such as 1.0.0 or 1.0.0-beta.1")
    return app_version.startswith("0.") or "-" in app_version


def version(root: Path = ROOT) -> str:
    desktop = root / "apps/desktop"
    versions = {
        read_json(desktop / "package.json")["version"],
        read_json(desktop / "package-lock.json")["version"],
        read_json(desktop / "package-lock.json")["packages"][""]["version"],
        read_json(desktop / "src-tauri/tauri.conf.json")["version"],
        tomllib.loads((desktop / "src-tauri/Cargo.toml").read_text())["package"][
            "version"
        ],
        next(
            p["version"]
            for p in tomllib.loads((desktop / "src-tauri/Cargo.lock").read_text())[
                "package"
            ]
            if p["name"] == "yomimado" and "source" not in p
        ),
    }
    if len(versions) != 1:
        raise ValueError(
            "App, npm and Cargo versions must agree before merging to main"
        )
    result = versions.pop()
    is_prerelease(result)
    return result


def normalized(path: str, text: str) -> dict:
    """Allow app version bumps, but keep dependency/build settings reviewed."""
    data = json.loads(text) if path.endswith(".json") else tomllib.loads(text)
    if path.endswith("package-lock.json"):
        data.pop("version")
        data["packages"][""].pop("version")
    elif path.endswith(("package.json", "tauri.conf.json")):
        data.pop("version")
    elif path.endswith("Cargo.toml"):
        data["package"].pop("version")
    elif path.endswith("Cargo.lock"):
        for package in data["package"]:
            if package["name"] == "yomimado" and "source" not in package:
                package.pop("version")
    return data


def runtime_compatible_config(path: str, before: str, after: str) -> bool:
    old = normalized(path, before)
    new = normalized(path, after)
    if path == "apps/desktop/src-tauri/Cargo.toml":
        # The 0.2.2 tray review confirms identical locked registry packages,
        # sources and notices to the approved seed. The native app is rebuilt;
        # this one feature does not change the reused frozen Python runtime.
        old_features = old["dependencies"]["tauri"].get("features", [])
        new_features = new["dependencies"]["tauri"].get("features", [])
        if "tray-icon" not in old_features and "tray-icon" in new_features:
            new_features.remove("tray-icon")
    return old == new


def verify_reuse(root: Path = ROOT) -> None:
    configs = {
        "apps/desktop/package.json",
        "apps/desktop/package-lock.json",
        "apps/desktop/src-tauri/tauri.conf.json",
        "apps/desktop/src-tauri/Cargo.toml",
        "apps/desktop/src-tauri/Cargo.lock",
    }
    allowed_prefixes = (
        "docs/",
        "apps/desktop/src/",
        "apps/desktop/src-tauri/src/",
        "packages/shared/src/",
        "scripts/tests/",
    )
    allowed_files = {
        # Retired workflow paths stay allowed so their removal relative to the
        # reviewed seed does not invalidate its unchanged runtime. Their original
        # definitions remain recoverable in Git history.
        "README.md",
        "CHANGELOG.md",
        "AGENTS.md",
        ".gitignore",
        "scripts/README.md",
        "scripts/update_version.py",
        # Standalone, pinned maintainer notes tooling; never frozen or bundled.
        "cliff.toml",
        "scripts/release_notes.py",
        "THIRD_PARTY_LICENSES/git-cliff/README.md",
        "THIRD_PARTY_LICENSES/git-cliff/LICENSE-MIT",
        # Reviewed 0.2.2 native tray inputs; none enter the frozen OCR runtime.
        # Keep this exact file list rather than allowing arbitrary icon/build
        # changes or relaxing the dependency/lock comparison below.
        "apps/desktop/src-tauri/build.rs",
        "apps/desktop/src-tauri/windows-app-manifest.xml",
        "apps/desktop/src-tauri/icons/tray-template.png",
        "apps/desktop/src-tauri/icons/tray-windows.png",
        "scripts/generate_tray_icons.py",
        "THIRD_PARTY_LICENSES/system-tray-review.md",
        ".github/workflows/release.yml",
        ".github/workflows/checks.yml",
        ".github/workflows/macos-prerelease.yml",
        ".github/workflows/desktop-release-checks.yml",
        ".github/workflows/desktop-release-resume.yml",
        "scripts/macos-ci-release.py",
        "scripts/desktop_release.py",
        # These inputs are used only by the independent Windows candidate path.
        # Shared OCR code, existing locks and macOS recipes still fail closed.
        ".github/workflows/windows-candidate.yml",
        ".github/workflows/windows-geos-audit.yml",
        "scripts/build-geos-windows.py",
        "scripts/geos-windows-probe.py",
        ".github/workflows/windows-opencv-audit.yml",
        "scripts/build-opencv-windows.py",
        "scripts/opencv-windows-probe.py",
        "scripts/windows_opencv_runtime.py",
        "scripts/windows_onnx_sources.py",
        "scripts/windows_native_sources.py",
        "scripts/windows_sudachi_runtime.py",
        "scripts/windows_vc_runtime.py",
        "scripts/windows_webview_runtime.py",
        "scripts/windows_export_inputs.py",
        "scripts/windows_python_rust_sources.py",
        "scripts/windows_nsis_plugin.py",
        "scripts/verify-windows-installer-terms.ps1",
        "THIRD_PARTY_LICENSES/windows-microsoft-components.txt",
        ".github/workflows/windows-vc-provenance.yml",
        ".github/workflows/webview-loader-probe.yml",
        "scripts/probe_webview_loader.py",
        "scripts/probe-webview-loader.cpp",
        "scripts/source-webview-loader.cpp",
        ".github/workflows/windows-onnx-prototype.yml",
        "scripts/onnx-probe-inputs.json",
        "scripts/onnx_generation.py",
        "scripts/onnx_detector.py",
        "scripts/onnx_runtime.py",
        "scripts/export_onnx_models.py",
        "scripts/verify_onnx_models.py",
        "scripts/prepare_windows_onnx.py",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/coloredlogs/LICENSE.txt",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/flatbuffers/LICENSE",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/humanfriendly/LICENSE.txt",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/pyreadline3/LICENSE.md",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/ml_dtypes/LICENSE",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/ml_dtypes/LICENSE.eigen",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/onnx/LICENSE",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/onnxruntime/LICENSE",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/onnxruntime/ThirdPartyNotices.txt",
        "apps/desktop/src-tauri/tauri.windows-release.conf.json",
        "scripts/build-windows-prerelease.ps1",
        "scripts/verify-windows-install.ps1",
        "scripts/verify-windows-ui.ps1",
        "scripts/windows-ui-driver.ps1",
        "scripts/release_dictionaries.py",
        "scripts/windows_release.py",
        "scripts/release_api.py",
        "scripts/windows_notices.py",
        "scripts/windows_python.py",
        "scripts/smoke-windows-install.py",
        "scripts/fixtures/windows-ocr-horizontal.png",
        "scripts/fixtures/windows-ocr-vertical.png",
        "services/ocr/requirements-windows-release.txt",
        "services/ocr/windows-inputs.json",
        "services/ocr/windows-assets.json",
        "services/ocr/windows_packaged_main.py",
        "services/ocr/windows_onnx_backend.py",
        "services/ocr/windows_onnx_packaged_main.py",
        "services/ocr/tests/test_windows_packaged_main.py",
        "services/ocr/tests/test_windows_onnx_backend.py",
    }
    # These generated files and unused icons are not runtime inputs. Permit
    # their removal only; additions/modifications still require seed review.
    removable_prefixes = (
        "services/ocr/yomimado_ocr.egg-info/",
        "apps/desktop/src-tauri/gen/schemas/",
        "apps/desktop/src-tauri/icons/android/",
    )
    deleted = None
    changed = git("diff", "--name-only", SEED_REVISION, "HEAD", root=root).splitlines()
    if set(changed) & FRONTEND_DATA_HASHES.keys():
        verify_frontend_data(root)
    for path in changed:
        if Path(path).suffix.lower() in {".onnx", ".pt", ".pth", ".safetensors"}:
            raise ValueError("Model weights must not enter the release source: " + path)
        if path in configs:
            before = git("show", f"{SEED_REVISION}:{path}", root=root)
            after = git("show", f"HEAD:{path}", root=root)
            if runtime_compatible_config(path, before, after):
                continue
        elif (
            path in FRONTEND_DATA_HASHES
            or path in allowed_files
            or path.startswith(allowed_prefixes)
        ):
            continue
        elif path == "apps/desktop/src-tauri/icons/placeholder.svg" or path.startswith(
            removable_prefixes
        ):
            if deleted is None:
                deleted = set(
                    git(
                        "diff",
                        "--diff-filter=D",
                        "--name-only",
                        SEED_REVISION,
                        "HEAD",
                        root=root,
                    ).splitlines()
                )
            if path in deleted:
                continue
        raise ValueError(
            f"Reviewed runtime/source inputs changed: {path}; prepare and review a new seed"
        )


def prepare_sources(seed: Path, notices: Path, output: Path, root: Path = ROOT) -> None:
    verify_reuse(root)
    if git("status", "--porcelain", root=root):
        raise ValueError("CI source export requires a clean merged commit")
    revision = git("rev-parse", "HEAD", root=root)
    manifest = read_json(seed / "source-delivery.json")
    if manifest["projectRevision"] != SEED_REVISION:
        raise ValueError("Incorrect reviewed seed revision")
    frontend_data = verify_frontend_data(root)
    shutil.copytree(seed, output)
    project = next(e for e in manifest["components"] if e["id"] == "project:yomimado")
    old_archive = project["archive"]
    archive = output / f"yomimado-{revision}.tar.gz"
    subprocess.run(
        [
            "git",
            "archive",
            "--format=tar.gz",
            "--prefix=yomimado/",
            "--output=" + str(archive.resolve()),
            revision,
        ],
        cwd=root,
        check=True,
    )
    checksum = digest(archive)
    if old_archive != archive.name:
        (output / old_archive).unlink()
    project.update(
        archive=archive.name,
        sha256=checksum,
        originalArchiveSha256=checksum,
        licenseEvidence=f"GPL-3.0-only application software; separate CC-BY-SA-4.0 JLPT data (see ci-followup.json). Complete Git source at {revision}. Frozen dependency/runtime inputs match reviewed seed {SEED_REVISION}.",
    )
    manifest["projectRevision"] = revision
    followup = {
        "seedRevision": SEED_REVISION,
        "projectRevision": revision,
        "scope": "Rebuilt desktop source/version and separate frontend JLPT data; frozen OCR code, dependency sources and their licence choices unchanged. Original seed approval is not extended to the frontend dataset.",
        "frontendData": frontend_data,
        "status": "automated-input-comparison; no new human source or installer approval claimed",
    }
    manifest["ciFollowup"] = followup
    write_json(output / "ci-followup.json", followup)
    # Keep these additions separate from the original runtime notices/review.
    # Read committed bytes, just like the project archive and reuse guard.
    for path in FRONTEND_DATA_HASHES:
        target = notices / frontend_data["noticeDirectory"] / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(committed_bytes(path, root))
    write_json(notices / "frontend-data.json", frontend_data)
    project.setdefault("noticeFiles", []).append(
        "frontend-jlpt/THIRD_PARTY_LICENSES/jlpt/LICENSE.txt"
    )
    # Both manifests carry the added notice reference.
    write_json(output / "source-delivery.json", manifest)
    worksheet = read_json(output / "source-delivery.worksheet.json")
    worksheet["projectRevision"] = revision
    next(e for e in worksheet["components"] if e["id"] == "project:yomimado").update(
        project
    )
    write_json(output / "source-delivery.worksheet.json", worksheet)
    omissions = read_json(output / "source-asset-omissions.json")
    omissions["archives"].pop(old_archive)
    omissions["archives"][archive.name] = {
        "originalSha256": checksum,
        "deliverySha256": checksum,
    }
    write_json(output / "source-asset-omissions.json", omissions)
    for name in ("BUILD.md", "REVIEW.md"):
        with (output / name).open("a") as stream:
            stream.write(
                f"\n\nCI desktop release at {revision}: see ci-followup.json. Original review/rebuild reports describe the seed and retain their original approval scope. Full filtered-source-only rebuilding remains unverified. Installer confirmation is required for this new DMG.\n"
            )
    shutil.copyfile(output / "source-delivery.json", notices / "source-delivery.json")
    (notices / "project-revision.txt").write_text(revision + "\n")
    shutil.copytree(notices, output / "notices", dirs_exist_ok=True)


def package(directory: Path, sources: Path, notices: Path) -> dict:
    app_version = version()
    revision = git("rev-parse", "HEAD")
    prefix = f"YomiMado_{app_version}"
    for source, name in (
        (sources, prefix + "_sources.tar.gz"),
        (notices, prefix + "_notices.tar.gz"),
    ):
        with tarfile.open(directory / name, "w:gz") as archive:
            archive.add(
                source,
                arcname="YomiMado-sources" if source == sources else "YomiMado-notices",
            )
    names = [
        prefix + "_aarch64.dmg",
        prefix + "_sources.tar.gz",
        prefix + "_notices.tar.gz",
    ]
    component = notices / "translation-component.json"
    if component.is_file():
        from translation_component import copy_component, read_manifest

        if read_manifest(component)["backend"] != "torch":
            raise ValueError("macOS optional translation component must use Torch")
        seed_name = copy_component(
            component, ROOT / "services/ocr/build/translation-components", directory
        )
        # The verified seed may predate the app version. Preserve its archive
        # bytes/descriptor while publishing the copy under this release's name.
        release_name = prefix + "_translation_torch.zip"
        if seed_name != release_name:
            (directory / seed_name).rename(directory / release_name)
        names.append(release_name)
    assets = {name: digest(directory / name) for name in names}
    record = {
        "sourceRevision": revision,
        "version": app_version,
        "tag": "v" + app_version,
        "prerelease": is_prerelease(app_version),
        "mode": "unnotarized-hobby",
        "installedAppVerified": False,
        "assets": assets,
    }
    if component.is_file():
        record["optionalTranslation"] = True
    for name, checksum in assets.items():
        (directory / (name + ".sha256")).write_text(f"{checksum}  {name}\n")
    write_json(directory / "release-candidate.json", record)
    return record


def verify_artifact(directory: Path, expected: dict) -> None:
    prefix = f"YomiMado_{expected['version']}"
    names = {
        prefix + suffix
        for suffix in ("_aarch64.dmg", "_sources.tar.gz", "_notices.tar.gz")
    }
    if expected.get("optionalTranslation") is True:
        names.add(prefix + "_translation_torch.zip")
    if (
        set(expected["assets"]) != names
        or expected["tag"] != "v" + expected["version"]
        or expected.get("prerelease") is not is_prerelease(expected["version"])
        or expected["mode"] != "unnotarized-hobby"
        or expected["installedAppVerified"] is not False
        or not re.fullmatch(r"[0-9a-f]{40}", expected["sourceRevision"])
    ):
        raise ValueError("Invalid candidate provenance")
    all_names = names | {n + ".sha256" for n in names} | {"release-candidate.json"}
    if {p.name for p in directory.iterdir()} != all_names:
        raise ValueError("Unexpected or missing release files")
    if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
        raise ValueError("Release files must be regular files")
    for name, checksum in expected["assets"].items():
        if (
            not re.fullmatch(r"[0-9a-f]{64}", checksum)
            or digest(directory / name) != checksum
        ):
            raise ValueError("Transferred artifact hash mismatch: " + name)
        if (directory / (name + ".sha256")).read_text() != f"{checksum}  {name}\n":
            raise ValueError("Incorrect checksum sidecar")
    if read_json(directory / "release-candidate.json") != expected:
        raise ValueError("Candidate provenance changed during transfer")


def verify_environment(data: dict, policies: dict) -> None:
    if (
        data.get("name") != "desktop-release"
        or data.get("can_admins_bypass") is not False
        or data.get("deployment_branch_policy")
        != {"protected_branches": False, "custom_branch_policies": True}
        or [(p.get("name"), p.get("type")) for p in policies.get("branch_policies", [])]
        != [("main", "branch")]
        or not any(
            r.get("type") == "required_reviewers" and r.get("reviewers")
            for r in data.get("protection_rules", [])
        )
    ):
        raise ValueError(
            "desktop-release needs a required reviewer, no administrator bypass, and a main-only branch rule"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "plan",
            "verify-reuse",
            "prepare-sources",
            "package",
            "verify-artifact",
            "verify-environment",
        ),
    )
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--notices", type=Path)
    parser.add_argument("--expected")
    parser.add_argument("--policies", type=Path)
    args = parser.parse_args()
    if args.action == "plan":
        app_version = version()
        print(
            json.dumps(
                {
                    "version": app_version,
                    "tag": "v" + app_version,
                    "prerelease": is_prerelease(app_version),
                }
            )
        )
    elif args.action == "verify-reuse":
        verify_reuse()
    elif args.action == "prepare-sources":
        prepare_sources(args.sources, args.notices, args.directory)
    elif args.action == "package":
        print(
            json.dumps(
                package(args.directory, args.sources, args.notices),
                separators=(",", ":"),
            )
        )
    elif args.action == "verify-artifact":
        expected = json.loads(args.expected)
        if expected["sourceRevision"] != os.environ["GITHUB_SHA"]:
            raise ValueError("Artifact does not belong to this merged commit")
        verify_artifact(args.directory, expected)
    else:
        verify_environment(read_json(args.directory), read_json(args.policies))


if __name__ == "__main__":
    main()
