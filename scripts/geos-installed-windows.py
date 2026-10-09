"""Test GEOS replacement in the exact private installer on a disposable runner.

Downloads read-only draft assets, never stages or publishes anything. The original
installer stays unchanged. Replacement is restored even after a smoke failure.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from windows_private_draft import API, request
from windows_release import ROOT, digest, fetch, read_json, verify_resources, write_json

REVISION = "c69eff996f7e85ea88ecb4f0407e05cf5d8ec8b5"
SETUP = "YomiMado_0.1.0_x64-setup.exe"
SETUP_SHA256 = "51b0091103c10c03ecd3748039bd4db0631381fb43885fe7163b889821fba207"
PROVENANCE_SHA256 = "aa69d7008c69c31ec5840448fe7e30829a12dc50922f744c815de5952358e95b"
RUNTIME_SHA256 = "c9911d9abe692c86f9de803af9f97cbb59af10339583dd86c8a673f036b73398"
DESKTOP_SHA256 = "8ea510ab664dfbdbd6c14b0b8f55ebf3e20361487eaa413676bcb78d5baf5e47"
BUILD = ROOT / "services/ocr/build/windows-geos-audit"


class AssetRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlparse(newurl)
        if parsed.scheme != "https" or parsed.hostname not in {
            "release-assets.githubusercontent.com",
            "api.github.com",
        }:
            raise ValueError("Unexpected GitHub asset redirect destination")
        # The signed storage URL is sufficient; never forward the job token.
        return Request(newurl, headers={"User-Agent": "YomiMado-native-audit"})


def download_asset(asset: dict, destination: Path, expected: str) -> None:
    if asset.get("state") != "uploaded" or asset.get("digest") != "sha256:" + expected:
        raise ValueError("Private asset identity/digest differs")
    req = Request(
        API + "/releases/assets/" + str(int(asset["id"])),
        headers={
            "Authorization": "Bearer " + os.environ["GH_TOKEN"],
            "Accept": "application/octet-stream",
            "User-Agent": "YomiMado-native-audit",
        },
    )
    with (
        build_opener(AssetRedirect()).open(req, timeout=600) as response,
        destination.open("wb") as output,
    ):
        shutil.copyfileobj(response, output)
    if digest(destination) != expected:
        raise ValueError("Downloaded private asset checksum differs")


def verify_candidate(release: dict, provenance: dict) -> None:
    if (
        release.get("draft") is not True
        or release.get("target_commitish") != REVISION
        or release.get("tag_name") != "windows-private-test-" + REVISION
        or provenance.get("sourceRevision") != REVISION
        or provenance.get("mode") != "private-test"
        or provenance.get("installedAppVerified") is not False
        or provenance.get("publicDistributionApproved") is not False
        or provenance.get("assets", {}).get(SETUP) != SETUP_SHA256
    ):
        raise ValueError("Exact private candidate identity/gates differ")


def snapshot(directory: Path) -> dict[str, str]:
    return {
        p.relative_to(directory).as_posix(): digest(p)
        for p in sorted(directory.rglob("*"))
        if p.is_file()
    }


def verify_smoke(report: dict, expected: dict[str, str]) -> None:
    if report.get("runtimeSha256") != RUNTIME_SHA256 or set(
        report.get("geometry", [])
    ) != {"vertical", "horizontal"}:
        raise ValueError("Incorrect installed service/OCR geometry evidence")
    if not all(
        report.get(key) is True
        for key in (
            "tokenization",
            "dictionaries",
            "kanji",
            "uncachedTranslation",
            "savedDataAndTranslationCacheSurvivedRestart",
        )
    ):
        raise ValueError("Installed learning/persistence did not pass")
    actual = {
        str(Path(m["path"]).resolve()).lower(): m["sha256"]
        for m in report.get("loadedModules", [])
        if Path(m["path"]).name.lower().startswith("geos")
        and Path(m["path"]).suffix.lower() == ".dll"
    }
    wanted = {str(Path(p).resolve()).lower(): h for p, h in expected.items()}
    if len(wanted) != 2 or actual != wanted:
        raise ValueError("Installed OCR loaded incorrect GEOS paths/hashes")


def verify_changes(before: dict, after: dict, removed: list[str], copies: dict) -> None:
    expected = dict(before)
    for name in removed:
        del expected[name]
    expected.update(copies)
    if after != expected:
        raise ValueError("Replacement changed files outside the exact GEOS plan")


def main() -> None:
    if sys.platform != "win32" or os.environ.get("GITHUB_ACTIONS") != "true":
        raise ValueError("Requires disposable Windows Actions execution")
    # This venv has the pinned pefile dependency used by the existing PE parser.
    spec = importlib.util.spec_from_file_location(
        "geos_build", ROOT / "scripts/build-geos-windows.py"
    )
    geos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(geos)
    audit = read_json(BUILD / "replacement-verification.json")
    if audit.get("passed") is not True:
        raise ValueError("Pinned GEOS build/frozen replacement must pass first")
    selected = [
        r
        for r in request(API + "/releases?per_page=100")
        if r["tag_name"] == "windows-private-test-" + REVISION
    ]
    if len(selected) != 1:
        raise ValueError("Missing or ambiguous exact private draft")
    release = selected[0]
    if release.get("draft") is not True or release.get("target_commitish") != REVISION:
        raise ValueError("Private release identity differs")
    assets = {a["name"]: a for a in release["assets"]}
    if len(assets) != len(release["assets"]):
        raise ValueError("Duplicate private release asset names")
    temporary = Path(os.environ["RUNNER_TEMP"]) / "yomimado-geos-installed"
    temporary.mkdir(exist_ok=True)
    download_asset(
        assets["windows-candidate.json"],
        temporary / "windows-candidate.json",
        PROVENANCE_SHA256,
    )
    verify_candidate(release, read_json(temporary / "windows-candidate.json"))
    installer = temporary / SETUP
    download_asset(assets[SETUP], installer, SETUP_SHA256)
    installed = Path(os.environ["LOCALAPPDATA"]) / "YomiMado"
    if installed.exists():
        raise ValueError("Disposable runner already has an installation")
    subprocess.run([str(installer), "/S", "/D=" + str(installed)], check=True)
    verify_resources(installed / "ocr")
    if digest(installed / "yomimado.exe") != DESKTOP_SHA256:
        raise ValueError("Installed desktop differs from tested candidate")
    runtime = installed / "ocr/runtime"
    if digest(runtime / "yomimado-ocr.exe") != RUNTIME_SHA256:
        raise ValueError("Installed service differs from tested candidate")
    model = temporary / "comictextdetector.pt.onnx"
    fetch(
        read_json(ROOT / "docs/windows-opencv-build-inputs.json")["smokeDetector"],
        model,
    )
    plan = geos.replacement_plan(runtime / "_internal", BUILD / "geos-install/bin")
    before = snapshot(installed)
    backup = temporary / "original-geos"
    backup.mkdir(exist_ok=True)
    for p in plan["remove"]:
        shutil.copy2(p, backup / p.name)

    def smoke(name: str, expected: dict) -> dict:
        result = ROOT / "services/ocr/build/windows/installed-smoke.json"
        result.unlink(missing_ok=True)
        geos.run(
            [
                sys.executable,
                str(ROOT / "scripts/smoke-windows-install.py"),
                str(installed),
                "--detector-model",
                str(model),
            ],
            name,
        )
        report = read_json(result)
        verify_smoke(report, expected)
        write_json(BUILD / (name + ".json"), report)
        return report

    try:
        baseline = smoke(
            "installed-baseline", {str(p): digest(p) for p in plan["remove"]}
        )
        for p in plan["remove"]:
            p.unlink()
        for src, dst in plan["copy"]:
            shutil.copy2(src, dst)
        copies = {
            dst.relative_to(installed).as_posix(): digest(src)
            for src, dst in plan["copy"]
        }
        verify_changes(
            before,
            snapshot(installed),
            [p.relative_to(installed).as_posix() for p in plan["remove"]],
            copies,
        )
        replacement = smoke(
            "installed-replacement",
            {str(dst): digest(src) for src, dst in plan["copy"]},
        )
        write_json(
            BUILD / "installed-replacement-verification.json",
            {
                "passed": True,
                "scope": "Exact private setup installed service; disposable GEOS replacement only",
                "installerSha256": SETUP_SHA256,
                "installerSourceRevision": REVISION,
                "auditRevision": os.environ["GITHUB_SHA"],
                "recipeSha256": digest(Path(__file__)),
                "unchangedInstalledFiles": len(before) - len(plan["remove"]),
                "removedLibraries": {
                    p.relative_to(installed).as_posix(): before[
                        p.relative_to(installed).as_posix()
                    ]
                    for p in plan["remove"]
                },
                "replacementLibraries": copies,
                "baseline": baseline,
                "replacement": replacement,
                "sourceCoverageApproved": False,
                "publicDistributionApproved": False,
                "windows11HardwareVerified": False,
            },
        )
    finally:
        for _, dst in plan["copy"]:
            dst.unlink(missing_ok=True)
        for p in plan["remove"]:
            shutil.copy2(backup / p.name, p)
        model.unlink(missing_ok=True)
        if snapshot(installed) != before:
            raise ValueError("Original installed files were not restored exactly")
    print(
        "Exact installed OCR/learning GEOS replacement passed; original installation restored. Source/public/installer approval remains open."
    )


if __name__ == "__main__":
    main()
