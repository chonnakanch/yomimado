"""Hash-bound inputs and combined macOS/Windows release artifacts.

Private seed access is GET-only on protected main, without build approval. Builders receive
hashed artifacts without credentials; only the protected publisher creates
the shared version tag and release. Build records never claim human approval.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import tarfile
import time
from pathlib import Path
from urllib.request import Request, build_opener

from release_api import API, REPOSITORY, candidate_files, request
from release_dictionaries import NAMES, SafeRedirect, restore
from windows_release import BUILD, RESOURCES, SERVICE, digest, read_json, write_json

spec = importlib.util.spec_from_file_location(
    "macos_ci", Path(__file__).with_name("macos-ci-release.py")
)
macos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(macos)

WINDOWS_SEED = "f8396ccd5e7352a62e526c68438cc7f3c9cedc60"
INPUTS = {
    "macos": {
        "tag": "macos-reviewed-seed-f1b4fba",
        "assets": {
            "YomiMado_0.3.0_aarch64.dmg": "45175e90fcb116a9c8ac3b910f6b15a4bec8e436db94a97f09eada087d88f8eb",
            "YomiMado_0.3.0_notices_f1b4fba.tar.gz": "9c124cf7803f0de74a69873638825ca3ac194043b5722da9c04f59b8b39d462c",
            "YomiMado_0.3.0_sources_f1b4fba.tar.gz": "3d70eef8361bead6b48d056c1d8c9dd71c90bedbd64ad2dcbb9b42d4b788ceb5",
            "YomiMado_0.3.0_translation_torch.zip": "e1c6a0ae58777d1eb4e8085eddff7a908fe0035e95c82178707178b7690434ef",
        },
    },
    "windows": {
        "tag": "windows-private-test-" + WINDOWS_SEED,
        "assets": {
            "windows-dictionary-snapshots.tar.gz": "077d6b93a5691a17aee7d8847b832b7c844f45b11270614b2eca50a9b35c5654"
        },
    },
}
ASSET_LIMIT = 2 * 1024**3
LAYOUT = "consolidated-v1"
SPLIT_LAYOUT = "platform-sources-v1"
SPLIT_COMPONENT_LAYOUT = "platform-sources-optional-translation-v1"
COMBINED_LAYOUTS = {
    LAYOUT,
    "combined-optional-translation-v1",
    SPLIT_LAYOUT,
    SPLIT_COMPONENT_LAYOUT,
}


def main_scope() -> None:
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    allowed_event = event_name == "workflow_dispatch"
    if event_name == "pull_request" and os.environ.get("GITHUB_EVENT_PATH"):
        event = read_json(Path(os.environ["GITHUB_EVENT_PATH"]))
        pr = event.get("pull_request", {})
        head = pr.get("head", {})
        allowed_event = (
            event.get("action") == "closed"
            and pr.get("merged") is True
            and pr.get("base", {}).get("ref") == "main"
            and pr.get("base", {}).get("repo", {}).get("full_name") == REPOSITORY
            and head.get("repo", {}).get("full_name") == REPOSITORY
            and head.get("ref", "").startswith("release/")
            and pr.get("merge_commit_sha") == os.environ.get("GITHUB_SHA")
        )
    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
        or not allowed_event
        or not re.fullmatch(r"[0-9a-f]{40}", os.environ.get("GITHUB_SHA", ""))
    ):
        raise ValueError(
            "Release input access requires main and a merged release/* PR or manual dispatch"
        )


class ChecksPending(ValueError):
    """The exact main commit has no completed gates result yet."""


def verify_main_checks(report: dict) -> None:
    """Require completed GitHub Actions gates on the selected commit, not a PR SHA."""
    revision = os.environ.get("GITHUB_SHA", "")
    runs = report.get("check_runs") if isinstance(report, dict) else None
    if (
        not re.fullmatch(r"[0-9a-f]{40}", revision)
        or not isinstance(runs, list)
        or report.get("total_count") != len(runs)
        or len(runs) >= 100
    ):
        raise ValueError("Invalid or incomplete main Checks report")
    gates = [
        run
        for run in runs
        if run.get("name") == "gates" and run.get("app", {}).get("id") == 15368
    ]
    if not runs or (
        len(gates) == 1
        and gates[0].get("head_sha") == revision
        and gates[0].get("status") in {"queued", "in_progress", "waiting", "pending"}
        and gates[0].get("conclusion") is None
    ):
        raise ChecksPending(
            "Release requires successful Checks; exact main gates pending"
        )
    if (
        len(gates) != 1
        or gates[0].get("head_sha") != revision
        or gates[0].get("status") != "completed"
        or gates[0].get("conclusion") != "success"
    ):
        raise ValueError(
            "Release requires successful Checks / gates for the exact main commit"
        )


def wait_main_checks(path: Path) -> None:
    """Allow main push Checks up to 15 minutes to complete after the PR closes."""
    main_scope()
    revision = os.environ["GITHUB_SHA"]
    for attempt in range(91):
        report = request(
            f"{API}/commits/{revision}/check-runs?check_name=gates&filter=latest&per_page=100"
        )
        write_json(path, report)
        try:
            verify_main_checks(report)
            return
        except ChecksPending:
            if attempt == 90:
                raise ValueError(
                    "Timed out waiting for successful Checks on main"
                ) from None
            print("Waiting for Checks / gates on " + revision, flush=True)
            time.sleep(10)


def verify_main_rules(rules: list[dict]) -> None:
    """Require effective main protections using the metadata-only rules API.

    GitHub omits disabled/evaluate rules here. Bypass actors are not exposed
    to the job token; the empty bypass list is verified in owner settings.
    """
    if not isinstance(rules, list) or len(rules) >= 100:
        raise ValueError("Invalid or truncated effective main rules")
    types = {r.get("type") for r in rules}
    checks = [
        r.get("parameters", {})
        for r in rules
        if r.get("type") == "required_status_checks"
    ]
    if not {"pull_request", "deletion", "non_fast_forward"}.issubset(types) or not any(
        c.get("strict_required_status_checks_policy") is True
        and any(
            check.get("context") == "gates" and check.get("integration_id") == 15368
            for check in c.get("required_status_checks", [])
        )
        for c in checks
    ):
        raise ValueError(
            "Main requires pull requests, GitHub Actions gates, current-base checks and deletion/force-push protection"
        )


def seed_release(releases: list[dict], platform: str) -> dict:
    pinned = INPUTS[platform]
    matches = [r for r in releases if r.get("tag_name") == pinned["tag"]]
    if len(matches) != 1 or matches[0].get("draft") is not True:
        raise ValueError("Missing, ambiguous or published private seed: " + platform)
    release = matches[0]
    if platform == "windows" and release.get("target_commitish") != WINDOWS_SEED:
        raise ValueError("Windows dictionary seed target differs")
    for name, sha in pinned["assets"].items():
        matches = [a for a in release["assets"] if a.get("name") == name]
        if (
            len(matches) != 1
            or type(matches[0].get("id")) is not int
            or matches[0].get("state") != "uploaded"
            or matches[0].get("digest") != "sha256:" + sha
        ):
            raise ValueError("Private seed asset identity differs: " + name)
    return release


def download_inputs(directory: Path) -> None:
    main_scope()
    if (
        request(API).get("default_branch") != "main"
        or request(API + "/git/ref/heads/main")["object"]["sha"]
        != os.environ["GITHUB_SHA"]
    ):
        raise ValueError("Private inputs require the current default main commit")
    verify_main_rules(request(API + "/rules/branches/main?per_page=100"))
    macos.verify_environment(
        request(API + "/environments/desktop-release"),
        request(API + "/environments/desktop-release/deployment-branch-policies"),
    )
    # The by-tag API does not reliably expose unpublished drafts. Enumerate
    # with a bounded, complete pagination pass and never send a mutation.
    releases = []
    for page in range(1, 21):
        batch = request(API + f"/releases?per_page=100&page={page}")
        releases.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise ValueError("Private release enumeration exceeded its bound")
    for platform, pinned in INPUTS.items():
        release = seed_release(releases, platform)
        output = directory / platform
        output.mkdir(parents=True, exist_ok=False)
        for name, sha in pinned["assets"].items():
            asset = next(a for a in release["assets"] if a["name"] == name)
            query = Request(
                API + "/releases/assets/" + str(asset["id"]),
                headers={
                    "Authorization": "Bearer " + os.environ["GH_TOKEN"],
                    "Accept": "application/octet-stream",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                method="GET",
            )
            path = output / name
            size = 0
            with (
                build_opener(SafeRedirect()).open(query, timeout=600) as response,
                path.open("xb") as stream,
            ):
                while data := response.read(1024**2):
                    size += len(data)
                    if size >= 2 * 1024**3:
                        raise ValueError("Reviewed input exceeds release asset limit")
                    stream.write(data)
            if digest(path) != sha:
                raise ValueError("Private input byte hash differs: " + name)
        verify_inputs(output, platform)
    print(
        "Private input hashes verified; no publication or installer approval performed"
    )


def verify_inputs(directory: Path, platform: str) -> None:
    expected = INPUTS[platform]["assets"]
    if {p.name for p in directory.iterdir()} != set(expected):
        raise ValueError("Unexpected or missing reviewed input files")
    for name, sha in expected.items():
        path = directory / name
        if path.is_symlink() or not path.is_file() or digest(path) != sha:
            raise ValueError("Transferred reviewed input changed: " + name)


def restore_dictionaries(directory: Path) -> None:
    main_scope()
    verify_inputs(directory, "windows")
    expected = {
        e["path"]: e["sha256"]
        for e in read_json(SERVICE / "windows-assets.json")
        if e["path"] in NAMES
    }
    restore(
        directory / "windows-dictionary-snapshots.tar.gz",
        RESOURCES / "assets",
        expected,
    )
    write_json(
        BUILD / "dictionary-seed.json",
        {
            "sourceRevision": WINDOWS_SEED,
            "archiveSha256": INPUTS["windows"]["assets"][
                "windows-dictionary-snapshots.tar.gz"
            ],
            "originals": expected,
            "scope": "dictionary-originals-only; protected hash-verified artifact transfer",
            "publicDistributionApproved": False,
        },
    )


def windows_names(version: str, components: bool = False) -> set[str]:
    return ({f"YomiMado_{version}_translation_onnx.zip"} if components else set()) | {
        f"YomiMado_{version}_x64-setup.exe",
        "windows-installer-inputs.json",
        "windows-notices.tar.gz",
        "windows-dictionary-snapshots.tar.gz",
        "windows-source-preparation.tar.gz",
        "project-sources.tar.gz",
        "windows-candidate.json",
        "SHA256SUMS.txt",
    }


def macos_names(version: str, components: bool = False) -> set[str]:
    primary = {
        f"YomiMado_{version}{suffix}"
        for suffix in ("_aarch64.dmg", "_sources.tar.gz", "_notices.tar.gz")
    }
    if components:
        primary.add(f"YomiMado_{version}_translation_torch.zip")
    return primary | {n + ".sha256" for n in primary} | {"release-candidate.json"}


def windows_record(directory: Path) -> dict:
    version = macos.version()
    revision = os.environ["GITHUB_SHA"]
    files = candidate_files(directory, revision)
    components = (directory / f"YomiMado_{version}_translation_onnx.zip").is_file()
    if {p.name for p in files} != windows_names(version, components):
        raise ValueError(
            "Windows release requires the exact versioned setup and source assets"
        )
    return {
        "sourceRevision": revision,
        "version": version,
        "tag": "v" + version,
        "prerelease": macos.is_prerelease(version),
        "platform": "windows-x64",
        "installedAppVerified": False,
        "assets": {p.name: digest(p) for p in files},
    }


def verify_windows(directory: Path, expected: dict) -> None:
    if windows_record(directory) != expected:
        raise ValueError("Windows release artifact provenance/digests differ")


def public_names(
    version: str, components: bool = False, *, split_sources: bool = False
) -> set[str]:
    return (
        (
            {
                f"YomiMado_{version}_translation_{backend}.zip"
                for backend in ("torch", "onnx")
            }
            if components
            else set()
        )
        | {
            f"YomiMado_{version}_{kind}.tar.gz"
            for kind in (
                ("sources_macos", "sources_windows") if split_sources else ("sources",)
            )
        }
        | {
            f"YomiMado_{version}{suffix}"
            for suffix in (
                "_aarch64.dmg",
                "_x64-setup.exe",
                "_notices.tar.gz",
            )
        }
    )


def bundle_members(version: str, kind: str, components: bool = False) -> dict[str, str]:
    """Retain every verified platform input except the two direct installers."""
    if kind not in (
        "sources",
        "sources_macos",
        "sources_windows",
        "notices",
        "notices_split",
    ):
        raise ValueError("Unknown release bundle kind")
    source_kind = kind.startswith("sources")
    source_platform = (
        kind.removeprefix("sources_") if kind.startswith("sources_") else None
    )
    sources = {
        f"macos/YomiMado_{version}_sources.tar.gz",
        "windows/project-sources.tar.gz",
        "windows/windows-source-preparation.tar.gz",
        "windows/windows-dictionary-snapshots.tar.gz",
    }
    members = {
        f"{platform}/{name}": name
        for platform, names in (
            ("macos", macos_names(version, components)),
            ("windows", windows_names(version, components)),
        )
        for name in names
        if not name.endswith((".dmg", ".exe", ".zip"))
        and ((f"{platform}/{name}" in sources) == source_kind)
    }
    if source_platform is not None:
        members = {
            name: filename
            for name, filename in members.items()
            if name.startswith(source_platform + "/")
        }
    return dict(sorted(members.items()))


def bundle_guide(version: str, kind: str, components: bool = False) -> bytes:
    if kind.startswith("sources"):
        text = f"""YomiMado {version} — corresponding sources and rebuild inputs

Extract this archive, then extract the original archives under macos/ and
windows/. Their bytes and internal paths are preserved from the verified
platform deliveries; platform-specific build recipes remain inside them.

macos/YomiMado_{version}_sources.tar.gz: reviewed macOS dependency/project
sources, notices, BUILD.md, REVIEW.md and original source coverage records.
windows/project-sources.tar.gz: the matching project, scripts and documentation.
windows/windows-source-preparation.tar.gz: Windows dependency sources and recipes.
windows/windows-dictionary-snapshots.tar.gz: exact original dictionary data.

Consult the build/review documents for platform-specific dependencies and terms.
A full source-only rebuild of the complete delivery remains unverified.
Detector ONNX weights are user-installed and excluded from this delivery.
"""
        if kind != "sources":
            platform = kind.removeprefix("sources_")
            text += f"""
This archive contains only the original {platform} source inputs listed above.
Download BOTH YomiMado_{version}_sources_macos.tar.gz and
YomiMado_{version}_sources_windows.tar.gz for the complete source delivery.
The original platform archives are preserved byte for byte. Both source parts
and the separate notices archive are bound by desktop-release-candidate.json
and desktop-SHA256SUMS.txt. No input has been omitted to meet the upload limit.
"""
    else:
        others = (
            ("eight" if components else "six")
            if kind == "notices_split"
            else ("seven" if components else "five")
        )
        text = f"""YomiMado {version} — notices and original verification records

Extract the platform notice archives under macos/ and windows/ to read the
original licences, copyright notices, source credits and component terms.
The other files retain the original platform candidate records, native input
inventory and checksums. No approval flags in these records have been rewritten.
Human installed-app tests and publication approval are recorded separately.

desktop-release-candidate.json binds both installers and these combined archives.
desktop-SHA256SUMS.txt checks all {others} other downloadable release files.
"""
    if components:
        text += "\nThe torch and ONNX translation ZIPs are separate optional downloads. Their exact hashes are bound by the platform/combined candidate records. Each includes model attribution and Apache-2.0 terms. Installers contain only OCR, learning data and the pinned download descriptor.\n"
    return text.encode("utf-8")


def bundle_outputs(split_sources: bool) -> dict[str, str]:
    """Public filename suffix -> archive membership/guide kind."""
    if split_sources:
        return {
            "sources_macos": "sources_macos",
            "sources_windows": "sources_windows",
            "notices": "notices_split",
        }
    return {"sources": "sources", "notices": "notices"}


def write_bundle(
    target: Path,
    directories: dict[str, Path],
    version: str,
    kind: str,
    components: bool = False,
) -> None:
    # Inputs are already compressed. A stored gzip stream avoids a slow second
    # compression pass; fixed headers make packaging independent of runner mtimes.
    with (
        target.open("xb") as stream,
        gzip.GzipFile(
            fileobj=stream, mode="wb", filename="", mtime=0, compresslevel=0
        ) as zipped,
        tarfile.open(fileobj=zipped, mode="w|", format=tarfile.USTAR_FORMAT) as archive,
    ):
        guide = bundle_guide(version, kind, components)
        member = tarfile.TarInfo("README.txt")
        member.size = len(guide)
        member.mode = 0o644
        archive.addfile(member, io.BytesIO(guide))
        for name, filename in bundle_members(version, kind, components).items():
            path = directories[name.split("/")[0]] / filename
            member = tarfile.TarInfo(name)
            member.size = path.stat().st_size
            member.mode = 0o644
            with path.open("rb") as source:
                archive.addfile(member, source)
    if target.stat().st_size >= ASSET_LIMIT:
        raise ValueError(
            f"Combined {kind} archive exceeds the upload limit; preserve all inputs "
            "and revise packaging before building another release"
        )


def verify_bundle(
    path: Path, version: str, kind: str, inputs: dict, components: bool = False
) -> None:
    members = bundle_members(version, kind, components)
    guide = bundle_guide(version, kind, components)
    hashes = {
        **{name: inputs[filename] for name, filename in members.items()},
        "README.txt": hashlib.sha256(guide).hexdigest(),
    }
    seen = set()
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            if (
                member.name not in hashes
                or member.name in seen
                or not member.isfile()
                or member.size >= ASSET_LIMIT
            ):
                raise ValueError(
                    "Unexpected, duplicate or unsafe combined archive member"
                )
            seen.add(member.name)
            with archive.extractfile(member) as stream:
                sha = hashlib.file_digest(stream, "sha256").hexdigest()
            if sha != hashes[member.name]:
                raise ValueError("Combined archive input hash differs: " + member.name)
    if seen != set(hashes):
        raise ValueError("Missing combined archive input")


def combine(
    mac_directory: Path,
    win_directory: Path,
    output: Path,
    mac_record: dict,
    win_record: dict,
) -> dict:
    macos.verify_artifact(mac_directory, mac_record)
    verify_windows(win_directory, win_record)
    for field in (
        "sourceRevision",
        "version",
        "tag",
        "prerelease",
        "installedAppVerified",
    ):
        if mac_record[field] != win_record[field]:
            raise ValueError("Platform candidate identity differs: " + field)
    if mac_record["sourceRevision"] != os.environ["GITHUB_SHA"]:
        raise ValueError("Combined artifacts do not belong to this main commit")
    output.mkdir(parents=True, exist_ok=False)
    version = mac_record["version"]
    components = mac_record.get("optionalTranslation") is True
    if (
        f"YomiMado_{version}_translation_onnx.zip" in win_record["assets"]
    ) != components:
        raise ValueError("Both platform translation components are required")
    directories = {"macos": mac_directory, "windows": win_directory}
    inputs = {
        p.name: digest(p)
        for source in directories.values()
        for p in sorted(source.iterdir())
    }
    for source, name in (
        (mac_directory, f"YomiMado_{version}_aarch64.dmg"),
        (win_directory, f"YomiMado_{version}_x64-setup.exe"),
    ):
        shutil.copyfile(source / name, output / name)
    for suffix, kind in bundle_outputs(True).items():
        write_bundle(
            output / f"YomiMado_{version}_{suffix}.tar.gz",
            directories,
            version,
            kind,
            components,
        )
    if components:
        for platform, backend in (("macos", "torch"), ("windows", "onnx")):
            name = f"YomiMado_{version}_translation_{backend}.zip"
            shutil.copyfile(directories[platform] / name, output / name)
    record = {
        "layout": SPLIT_COMPONENT_LAYOUT if components else SPLIT_LAYOUT,
        "sourceRevision": mac_record["sourceRevision"],
        "version": mac_record["version"],
        "tag": mac_record["tag"],
        "prerelease": mac_record["prerelease"],
        "platforms": ["macos-aarch64", "windows-x64"],
        "installedAppVerified": False,
        "platformCandidates": {"macos": mac_record, "windows": win_record},
        "inputs": inputs,
        "assets": {p.name: digest(p) for p in sorted(output.iterdir())},
    }
    write_json(output / "desktop-release-candidate.json", record)
    sums = {
        **record["assets"],
        "desktop-release-candidate.json": digest(
            output / "desktop-release-candidate.json"
        ),
    }
    (output / "desktop-SHA256SUMS.txt").write_text(
        "".join(f"{sha}  {name}\n" for name, sha in sums.items()), encoding="utf-8"
    )
    verify_combined(output, record)
    return record


def verify_combined(
    directory: Path, expected: dict, *, source_revision: str | None = None
) -> None:
    version = macos.version()
    layout = expected.get("layout")
    if layout is not None and (
        not isinstance(layout, str) or layout not in COMBINED_LAYOUTS
    ):
        raise ValueError("Unknown combined release layout")
    components = layout in ("combined-optional-translation-v1", SPLIT_COMPONENT_LAYOUT)
    split_sources = layout in (SPLIT_LAYOUT, SPLIT_COMPONENT_LAYOUT)
    # Keep the original 17-file v0.1.0 record readable without repackaging it.
    names = (
        public_names(version, components, split_sources=split_sources)
        if layout in COMBINED_LAYOUTS
        else macos_names(version) | windows_names(version)
    )
    if (
        expected.get("sourceRevision") != (source_revision or os.environ["GITHUB_SHA"])
        or not re.fullmatch(r"[0-9a-f]{40}", expected["sourceRevision"])
        or expected.get("version") != version
        or expected.get("tag") != "v" + version
        or expected.get("prerelease") is not macos.is_prerelease(version)
        or expected.get("platforms") != ["macos-aarch64", "windows-x64"]
        or expected.get("installedAppVerified") is not False
        or set(expected.get("assets", {})) != names
    ):
        raise ValueError("Invalid combined release identity/classification")
    names |= {"desktop-release-candidate.json", "desktop-SHA256SUMS.txt"}
    if {p.name for p in directory.iterdir()} != names:
        raise ValueError("Unexpected or missing combined release files")
    for path in directory.iterdir():
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size >= ASSET_LIMIT
        ):
            raise ValueError(
                "Release files must be regular and within the upload limit"
            )
    for name, sha in expected["assets"].items():
        if not re.fullmatch(r"[0-9a-f]{64}", sha) or digest(directory / name) != sha:
            raise ValueError("Combined artifact hash differs: " + name)
    if read_json(directory / "desktop-release-candidate.json") != expected:
        raise ValueError("Combined candidate record changed")
    sums = {
        **expected["assets"],
        "desktop-release-candidate.json": digest(
            directory / "desktop-release-candidate.json"
        ),
    }
    if (directory / "desktop-SHA256SUMS.txt").read_text() != "".join(
        f"{sha}  {name}\n" for name, sha in sums.items()
    ):
        raise ValueError("Combined checksums differ")
    if layout in COMBINED_LAYOUTS:
        inputs = expected.get("inputs", {})
        if set(inputs) != macos_names(version, components) | windows_names(
            version, components
        ) or any(not re.fullmatch(r"[0-9a-f]{64}", sha) for sha in inputs.values()):
            raise ValueError("Invalid combined input coverage")
        candidates = expected.get("platformCandidates", {})
        if set(candidates) != {"macos", "windows"}:
            raise ValueError("Missing platform candidate provenance")
        mac_json = (json.dumps(candidates["macos"], indent=2) + "\n").encode("utf-8")
        if hashlib.sha256(mac_json).hexdigest() != inputs["release-candidate.json"]:
            raise ValueError("Original macOS candidate record differs")
        for platform, candidate in candidates.items():
            if any(
                candidate.get(field) != expected[field]
                for field in (
                    "sourceRevision",
                    "version",
                    "tag",
                    "prerelease",
                    "installedAppVerified",
                )
            ):
                raise ValueError("Platform candidate identity differs")
            candidate_names = (
                {
                    f"YomiMado_{version}{suffix}"
                    for suffix in ("_aarch64.dmg", "_sources.tar.gz", "_notices.tar.gz")
                }
                if platform == "macos"
                else windows_names(version, components)
            )
            if components and platform == "macos":
                candidate_names.add(f"YomiMado_{version}_translation_torch.zip")
            if candidate.get("assets") != {
                name: inputs[name] for name in candidate_names
            }:
                raise ValueError("Platform candidate input hashes differ")
        for name in (
            f"YomiMado_{version}_aarch64.dmg",
            f"YomiMado_{version}_x64-setup.exe",
            *(
                [f"YomiMado_{version}_translation_{b}.zip" for b in ("torch", "onnx")]
                if components
                else []
            ),
        ):
            if inputs[name] != expected["assets"][name]:
                raise ValueError("Combined installer bytes differ from platform inputs")
        for suffix, kind in bundle_outputs(split_sources).items():
            verify_bundle(
                directory / f"YomiMado_{version}_{suffix}.tar.gz",
                version,
                kind,
                inputs,
                components,
            )


def select_uploaded_release(pages: list[list[dict]], expected: dict) -> int:
    """Select one exact draft from the paginated listing, never the by-tag API."""
    if (
        not isinstance(pages, list)
        or not pages
        or len(pages) > 20
        or any(not isinstance(page, list) or len(page) > 100 for page in pages)
        or len(pages[-1]) == 100
    ):
        raise ValueError("Invalid, incomplete or excessive release enumeration")
    matches = [
        item
        for page in pages
        for item in page
        if item.get("tag_name") == expected["tag"]
    ]
    if len(matches) != 1:
        raise ValueError("Missing or ambiguous uploaded release")
    report = matches[0]
    if (
        report.get("draft") is not True
        or report.get("target_commitish") != expected["sourceRevision"]
        or report.get("prerelease") is not expected["prerelease"]
        or report.get("name") != "YomiMado " + expected["tag"]
        or type(report.get("id")) is not int
        or report["id"] <= 0
    ):
        raise ValueError("Uploaded draft identity differs")
    return report["id"]


def verify_uploaded(
    directory: Path,
    expected: dict,
    report: dict,
    *,
    draft: bool = True,
    source_revision: str | None = None,
) -> None:
    verify_combined(directory, expected, source_revision=source_revision)
    assets = {p.name: "sha256:" + digest(p) for p in directory.iterdir()}
    if (
        report.get("draft") is not draft
        or report.get("tag_name") != expected["tag"]
        or report.get("target_commitish") != expected["sourceRevision"]
        or report.get("prerelease") is not expected["prerelease"]
        or len(report.get("assets", [])) != len(assets)
        or {a["name"]: a.get("digest") for a in report["assets"]} != assets
        or any(a.get("state") != "uploaded" for a in report["assets"])
    ):
        raise ValueError("Uploaded release differs; leave it unpublished")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "download-inputs",
            "verify-main-rules",
            "verify-main-checks",
            "wait-main-checks",
            "verify-inputs",
            "restore-dictionaries",
            "windows-record",
            "verify-windows",
            "combine",
            "verify-combined",
            "verify-uploaded",
            "verify-published",
            "select-uploaded-release",
        ),
    )
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--platform", choices=INPUTS)
    parser.add_argument("--macos", type=Path)
    parser.add_argument("--windows", type=Path)
    parser.add_argument("--expected")
    parser.add_argument("--macos-record")
    parser.add_argument("--windows-record")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.action == "download-inputs":
        download_inputs(args.directory)
    elif args.action == "verify-main-rules":
        verify_main_rules(read_json(args.directory))
    elif args.action == "verify-main-checks":
        verify_main_checks(read_json(args.directory))
    elif args.action == "wait-main-checks":
        wait_main_checks(args.directory)
    elif args.action == "verify-inputs":
        verify_inputs(args.directory, args.platform)
    elif args.action == "restore-dictionaries":
        restore_dictionaries(args.directory)
    elif args.action == "windows-record":
        print(json.dumps(windows_record(args.directory), separators=(",", ":")))
    elif args.action == "verify-windows":
        verify_windows(args.directory, json.loads(args.expected))
    elif args.action == "combine":
        record = combine(
            args.macos,
            args.windows,
            args.directory,
            json.loads(args.macos_record),
            json.loads(args.windows_record),
        )
        print(json.dumps(record, separators=(",", ":")))
    elif args.action == "verify-combined":
        verify_combined(args.directory, json.loads(args.expected))
    elif args.action == "select-uploaded-release":
        expected = json.loads(args.expected)
        verify_combined(args.directory, expected)
        print(select_uploaded_release(read_json(args.report), expected))
    else:
        verify_uploaded(
            args.directory,
            json.loads(args.expected),
            read_json(args.report),
            draft=args.action != "verify-published",
        )


if __name__ == "__main__":
    main()
