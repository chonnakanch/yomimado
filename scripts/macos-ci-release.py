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
from pathlib import Path

import tomllib

SEED_REVISION = "5120506bdf5cf5fa93e2780484985473038f2195"
ROOT = Path(__file__).resolve().parent.parent


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
        "README.md",
        ".github/workflows/macos-prerelease.yml",
        "scripts/macos-ci-release.py",
        # These inputs are used only by the independent Windows candidate path.
        # Shared OCR code, existing locks and macOS recipes still fail closed.
        ".github/workflows/windows-candidate.yml",
        ".github/workflows/windows-geos-audit.yml",
        "scripts/build-geos-windows.py",
        "scripts/geos-windows-probe.py",
        "scripts/geos-installed-windows.py",
        ".github/workflows/windows-opencv-audit.yml",
        "scripts/build-opencv-windows.py",
        "scripts/opencv-windows-probe.py",
        ".github/workflows/windows-onnx-prototype.yml",
        "scripts/onnx-probe-inputs.json",
        "scripts/onnx_generation.py",
        "scripts/onnx_detector_probe.py",
        "scripts/onnx_runtime_probe.py",
        "scripts/export_onnx_probe.py",
        "scripts/check_onnx_probe.py",
        "scripts/prepare_onnx_probe.py",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/coloredlogs/LICENSE.txt",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/flatbuffers/LICENSE",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/humanfriendly/LICENSE.txt",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/pyreadline3/LICENSE.md",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/ml_dtypes/LICENSE",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/ml_dtypes/LICENSE.eigen",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/onnx/LICENSE",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/onnxruntime/LICENSE",
        "THIRD_PARTY_LICENSES/windows-onnx-probe/onnxruntime/ThirdPartyNotices.txt",
        ".github/workflows/windows-torch-audit.yml",
        "scripts/build-torch-windows.py",
        "scripts/torch-windows-probe.py",
        "scripts/build-torchvision-windows.py",
        "scripts/torchvision-windows-probe.py",
        "apps/desktop/src-tauri/tauri.windows-release.conf.json",
        "scripts/build-windows-prerelease.ps1",
        "scripts/verify-windows-install.ps1",
        "scripts/verify-windows-ui.ps1",
        "scripts/windows_dictionary_seed.py",
        "scripts/windows_release.py",
        "scripts/windows_private_draft.py",
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
    changed = git("diff", "--name-only", SEED_REVISION, "HEAD", root=root).splitlines()
    for path in changed:
        if Path(path).suffix.lower() in {".onnx", ".pt", ".pth", ".safetensors"}:
            raise ValueError("Model weights must not enter the release source: " + path)
        if path in configs:
            before = git("show", f"{SEED_REVISION}:{path}", root=root)
            after = git("show", f"HEAD:{path}", root=root)
            if normalized(path, before) == normalized(path, after):
                continue
        elif path in allowed_files or path.startswith(allowed_prefixes):
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
        licenseEvidence=f"GPL-3.0-only; complete Git source at {revision}. Dependency/runtime inputs match reviewed seed {SEED_REVISION}.",
    )
    manifest["projectRevision"] = revision
    followup = {
        "seedRevision": SEED_REVISION,
        "projectRevision": revision,
        "scope": "Desktop source/version and release documentation/automation; dependency sources, frozen OCR code and licence choices unchanged.",
        "status": "automated-input-comparison; no new human source or installer approval claimed",
    }
    manifest["ciFollowup"] = followup
    write_json(output / "source-delivery.json", manifest)
    write_json(output / "ci-followup.json", followup)
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
        data.get("name") != "macos-release"
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
            "macos-release needs a required reviewer, no administrator bypass, and a main-only branch rule"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "plan",
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
