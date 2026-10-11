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
from urllib.error import HTTPError
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
# Original bytes from REVISION, also bound to the tested setup's inventory.
# Later source/notice additions must not redefine this historical installation.
MANIFEST_HASHES = {
    "windows-inputs.json": "1e75e22fa08eec1589cc517b6dbf9a88af6f043e6a3a74733a36f814103141cc",
    "windows-assets.json": "c5f745cfcfdd0f30fb11eeb52467c373bea9386b34a24ecd8fefe753e76e5878",
}
BUILD = ROOT / "services/ocr/build/windows-geos-audit"
INPUT_ENVIRONMENT = "windows-native-input"


def verify_input_protection(environment: dict, policies: dict) -> None:
    if (
        environment.get("name") != INPUT_ENVIRONMENT
        or environment.get("can_admins_bypass") is not False
        or environment.get("deployment_branch_policy")
        != {"protected_branches": False, "custom_branch_policies": True}
        or [(p.get("name"), p.get("type")) for p in policies.get("branch_policies", [])]
        != [("develop", "branch")]
        or not any(
            r.get("type") == "required_reviewers" and r.get("reviewers")
            for r in environment.get("protection_rules", [])
        )
    ):
        raise ValueError(
            "windows-native-input requires a human reviewer, no administrator "
            "bypass and a develop-only branch rule before private token access"
        )


def check_input_protection() -> None:
    endpoint = API + "/environments/" + INPUT_ENVIRONMENT
    try:
        verify_input_protection(
            request(endpoint), request(endpoint + "/deployment-branch-policies")
        )
    except HTTPError as error:
        if error.code in {403, 404}:
            raise RuntimeError(
                "Owner must configure reviewer-protected windows-native-input "
                "and its read-only draft-access secret; see the native worksheet."
            ) from None
        raise


def private_release() -> dict:
    # The by-tag endpoint is for published releases. Resolve this unpublished
    # input through the authenticated listing and still require its exact identity.
    tag = "windows-private-test-" + REVISION
    try:
        releases = request(API + "/releases?per_page=100")
    except HTTPError as error:
        if error.code in {401, 403, 404}:
            raise PrivateInputError(
                "github-http-" + str(error.code),
                "GitHub rejected the protected private-input GET (HTTP "
                + str(error.code)
                + "); provide protected access through WINDOWS_PRIVATE_INPUT_TOKEN.",
                error.code,
            ) from None
        raise
    if not isinstance(releases, list) or len(releases) >= 100:
        raise PrivateInputError(
            "incomplete-release-list", "Cannot establish a complete draft listing."
        )
    matches = [r for r in releases if r.get("tag_name") == tag]
    if len(matches) != 1:
        raise PrivateInputError(
            "exact-draft-not-visible",
            "The protected token cannot see exactly one matching private draft. "
            "Keep the draft unpublished and token permissions unchanged; "
            "the owner must check repository selection and draft visibility.",
        )
    release = matches[0]
    if (
        release.get("draft") is not True
        or release.get("target_commitish") != REVISION
        or release.get("tag_name") != tag
    ):
        raise ValueError("Private release identity differs")
    return release


class PrivateInputError(RuntimeError):
    def __init__(self, reason: str, message: str, status: int | None = None):
        super().__init__(message)
        self.reason = reason
        self.status = status


def check_private_draft() -> int:
    # Retain only fixed diagnostics, never exceptions, response bodies, headers,
    # URLs or credentials. This record is useful even when access fails early.
    report = {
        "passed": False,
        "installerSourceRevision": REVISION,
        "installerSha256": SETUP_SHA256,
        "sourceCoverageApproved": False,
        "publicDistributionApproved": False,
    }
    try:
        if not os.environ.get("GH_TOKEN", "").strip():
            raise PrivateInputError(
                "missing-environment-secret",
                "WINDOWS_PRIVATE_INPUT_TOKEN is missing or empty in windows-native-input.",
            )
        release = private_release()
        assets = {a["name"]: a for a in release["assets"]}
        if len(assets) != len(release["assets"]):
            raise ValueError("Duplicate assets")
        for name, sha in (
            (SETUP, SETUP_SHA256),
            ("windows-candidate.json", PROVENANCE_SHA256),
        ):
            asset = assets[name]
            if (
                asset.get("state") != "uploaded"
                or asset.get("digest") != "sha256:" + sha
            ):
                raise ValueError("Asset identity differs")
        report.update(passed=True, reason="exact-draft-visible")
        message = "Exact unpublished draft and declared asset digests verified; download byte checks remain required."
    except PrivateInputError as error:
        report.update(reason=error.reason, httpStatus=error.status)
        message = str(error)
    except (ValueError, KeyError, TypeError):
        report.update(reason="private-input-identity-mismatch")
        message = "Private draft identity or declared asset digests differ from the fixed tested setup."
    except (OSError, RuntimeError):
        report.update(reason="unexpected-preflight-failure")
        message = "Private-input GET failed before identity verification; inspect the runner/network without disclosing credentials."
    write_json(BUILD / "private-input-preflight.json", report)
    print(("" if report["passed"] else "::error::") + message)
    return 0 if report["passed"] else 1


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
    # Windows resolves these names without case sensitivity. Shapely's actual
    # frozen directory is Shapely.libs, while its replacement plan uses
    # shapely.libs. Keep exact content hashes without inventing a missing file.
    files = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            key = path.relative_to(directory).as_posix().casefold()
            if key in files:
                raise ValueError("Ambiguous Windows installed path casing")
            files[key] = digest(path)
    return files


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


def main(progress: dict) -> None:
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

    def phase(name: str) -> None:
        progress["phase"] = name
        write_json(BUILD / "installed-replacement-progress.json", progress)

    phase("resolve exact private draft")
    release = private_release()
    assets = {a["name"]: a for a in release["assets"]}
    if len(assets) != len(release["assets"]):
        raise ValueError("Duplicate private release asset names")
    temporary = Path(os.environ["RUNNER_TEMP"]) / "yomimado-geos-installed"
    temporary.mkdir(exist_ok=True)
    phase("download exact provenance")
    download_asset(
        assets["windows-candidate.json"],
        temporary / "windows-candidate.json",
        PROVENANCE_SHA256,
    )
    verify_candidate(release, read_json(temporary / "windows-candidate.json"))
    installer = temporary / SETUP
    phase("download exact installer")
    download_asset(assets[SETUP], installer, SETUP_SHA256)
    installed = Path(os.environ["LOCALAPPDATA"]) / "YomiMado"
    if installed.exists():
        raise ValueError("Disposable runner already has an installation")
    phase("install exact setup")
    subprocess.run([str(installer), "/S", "/D=" + str(installed)], check=True)
    phase("verify original installed resources")
    verify_resources(installed / "ocr", manifest_hashes=MANIFEST_HASHES)
    if digest(installed / "yomimado.exe") != DESKTOP_SHA256:
        raise ValueError("Installed desktop differs from tested candidate")
    runtime = installed / "ocr/runtime"
    if digest(runtime / "yomimado-ocr.exe") != RUNTIME_SHA256:
        raise ValueError("Installed service differs from tested candidate")
    model = temporary / "comictextdetector.pt.onnx"
    phase("obtain smoke-only detector")
    fetch(
        read_json(ROOT / "docs/windows-opencv-build-inputs.json")["smokeDetector"],
        model,
    )
    phase("resolve original GEOS layout")
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
        write_json(BUILD / (name + ".json"), report)
        verify_smoke(report, expected)
        return report

    try:
        phase("baseline installed OCR")
        baseline = smoke(
            "installed-baseline", {str(p): digest(p) for p in plan["remove"]}
        )
        phase("replace only GEOS libraries")
        for p in plan["remove"]:
            p.unlink()
        for src, dst in plan["copy"]:
            shutil.copy2(src, dst)
        copies = {
            dst.relative_to(installed).as_posix().casefold(): digest(src)
            for src, dst in plan["copy"]
        }
        verify_changes(
            before,
            snapshot(installed),
            [p.relative_to(installed).as_posix().casefold() for p in plan["remove"]],
            copies,
        )
        phase("replacement installed OCR")
        replacement = smoke(
            "installed-replacement",
            {str(dst): digest(src) for src, dst in plan["copy"]},
        )
        verification = {
            "passed": True,
            "scope": "Exact private setup installed service; disposable GEOS replacement only",
            "installerSha256": SETUP_SHA256,
            "installerSourceRevision": REVISION,
            "auditRevision": os.environ["GITHUB_SHA"],
            "recipeSha256": digest(Path(__file__)),
            "unchangedInstalledFiles": len(before) - len(plan["remove"]),
            "removedLibraries": {
                p.relative_to(installed).as_posix().casefold(): before[
                    p.relative_to(installed).as_posix().casefold()
                ]
                for p in plan["remove"]
            },
            "replacementLibraries": copies,
            "baseline": baseline,
            "replacement": replacement,
            "sourceCoverageApproved": False,
            "publicDistributionApproved": False,
            "windows11HardwareVerified": False,
        }
    except Exception:
        progress["failedPhase"] = progress["phase"]
        raise
    finally:
        # Diagnostic I/O must not interrupt restoration of the original DLLs.
        progress["phase"] = "restore original installed files"
        for _, dst in plan["copy"]:
            dst.unlink(missing_ok=True)
        for p in plan["remove"]:
            shutil.copy2(backup / p.name, p)
        model.unlink(missing_ok=True)
        if snapshot(installed) != before:
            raise ValueError("Original installed files were not restored exactly")
        progress["originalFilesRestored"] = True
    write_json(BUILD / "installed-replacement-verification.json", verification)
    progress.update(passed=True, phase="complete")
    write_json(BUILD / "installed-replacement-progress.json", progress)
    print(
        "Exact installed OCR/learning GEOS replacement passed; original installation restored. Source/public/installer approval remains open."
    )


if __name__ == "__main__":
    if sys.argv[1:] == ["--check-private-draft"]:
        sys.exit(check_private_draft())
    elif sys.argv[1:] == ["--check-input-protection"]:
        check_input_protection()
        print(
            "Required reviewer, no administrator bypass and develop-only input protection verified."
        )
    elif len(sys.argv) == 1:
        progress = {
            "passed": False,
            "phase": "validate source-built probe",
            "installerSourceRevision": REVISION,
            "installerSha256": SETUP_SHA256,
            "manifestHashes": MANIFEST_HASHES,
            "sourceCoverageApproved": False,
            "publicDistributionApproved": False,
        }
        try:
            main(progress)
        except Exception as error:
            # No exception text, response bodies or signed URLs in artifacts.
            progress["errorType"] = type(error).__name__
            if isinstance(error, HTTPError):
                progress["httpStatus"] = error.code
            write_json(BUILD / "installed-replacement-progress.json", progress)
            print(
                "::error::Exact installed GEOS check failed at: "
                + progress.get("failedPhase", progress["phase"])
            )
            raise
    else:
        raise ValueError("Expected no arguments or a private-input preflight")
