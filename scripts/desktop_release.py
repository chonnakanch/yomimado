"""Hash-bound inputs and combined macOS/Windows release artifacts.

Private seed access is GET-only on protected main, without build approval. Builders receive
hashed artifacts without credentials; only the protected publisher creates
the shared version tag and release. Build records never claim human approval.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
from pathlib import Path
from urllib.request import Request, build_opener

from windows_dictionary_seed import NAMES, SafeRedirect, restore
from windows_private_draft import API, REPOSITORY, candidate_files, request
from windows_release import BUILD, RESOURCES, SERVICE, digest, read_json, write_json

spec = importlib.util.spec_from_file_location(
    "macos_ci", Path(__file__).with_name("macos-ci-release.py")
)
macos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(macos)

WINDOWS_SEED = "f8396ccd5e7352a62e526c68438cc7f3c9cedc60"
INPUTS = {
    "macos": {
        "tag": "macos-reviewed-seed-5120506",
        "assets": {
            "YomiMado_0.1.0_aarch64.dmg": "fbe1d788d2f80b442b2abf9c53c5439af81ea78c2bc73c584907b4791f3c1cff",
            "YomiMado_0.1.0_sources_5120506.tar.gz": "0ca10a4cc5084d4778aa636e07c504db56dcf9baec87af2d37b00859803a2744",
            "YomiMado_0.1.0_notices_5120506.tar.gz": "f0d2a380e2639a525bf93c61d0aa0c45de5952cb283a9a0afb65810c46b22f71",
        },
    },
    "windows": {
        "tag": "windows-private-test-" + WINDOWS_SEED,
        "assets": {
            "windows-dictionary-snapshots.tar.gz": "e8ed381b9d1ee88b363be0264189359fb0923ed751a7b2aa5d84f7bde9b968be"
        },
    },
}


def main_scope() -> None:
    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
        or not re.fullmatch(r"[0-9a-f]{40}", os.environ.get("GITHUB_SHA", ""))
    ):
        raise ValueError(
            "Release input access requires this repository's main workflow"
        )


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
        request(API + "/environments/macos-release"),
        request(API + "/environments/macos-release/deployment-branch-policies"),
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


def windows_names(version: str) -> set[str]:
    return {
        f"YomiMado_{version}_x64-setup.exe",
        "windows-installer-inputs.json",
        "windows-notices.tar.gz",
        "windows-dictionary-snapshots.tar.gz",
        "windows-source-preparation.tar.gz",
        "project-sources.tar.gz",
        "windows-candidate.json",
        "SHA256SUMS.txt",
    }


def macos_names(version: str) -> set[str]:
    primary = {
        f"YomiMado_{version}{suffix}"
        for suffix in ("_aarch64.dmg", "_sources.tar.gz", "_notices.tar.gz")
    }
    return primary | {n + ".sha256" for n in primary} | {"release-candidate.json"}


def windows_record(directory: Path) -> dict:
    version = macos.version()
    revision = os.environ["GITHUB_SHA"]
    files = candidate_files(directory, revision)
    if {p.name for p in files} != windows_names(version):
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
    for source in (mac_directory, win_directory):
        for path in source.iterdir():
            shutil.copyfile(path, output / path.name)
    record = {
        "sourceRevision": mac_record["sourceRevision"],
        "version": mac_record["version"],
        "tag": mac_record["tag"],
        "prerelease": mac_record["prerelease"],
        "platforms": ["macos-aarch64", "windows-x64"],
        "installedAppVerified": False,
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


def verify_combined(directory: Path, expected: dict) -> None:
    version = macos.version()
    names = macos_names(version) | windows_names(version)
    if (
        expected.get("sourceRevision") != os.environ["GITHUB_SHA"]
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
            or path.stat().st_size >= 2 * 1024**3
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


def verify_uploaded(directory: Path, expected: dict, report: dict) -> None:
    verify_combined(directory, expected)
    assets = {p.name: "sha256:" + digest(p) for p in directory.iterdir()}
    if (
        report.get("draft") is not True
        or report.get("tag_name") != expected["tag"]
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
            "verify-inputs",
            "restore-dictionaries",
            "windows-record",
            "verify-windows",
            "combine",
            "verify-combined",
            "verify-uploaded",
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
    else:
        verify_uploaded(
            args.directory, json.loads(args.expected), read_json(args.report)
        )


if __name__ == "__main__":
    main()
