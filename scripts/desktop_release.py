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
ASSET_LIMIT = 2 * 1024**3
LAYOUT = "consolidated-v1"


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


def public_names(version: str) -> set[str]:
    return {
        f"YomiMado_{version}{suffix}"
        for suffix in (
            "_aarch64.dmg",
            "_x64-setup.exe",
            "_sources.tar.gz",
            "_notices.tar.gz",
        )
    }


def bundle_members(version: str, kind: str) -> dict[str, str]:
    """Retain every verified platform input except the two direct installers."""
    sources = {
        f"macos/YomiMado_{version}_sources.tar.gz",
        "windows/project-sources.tar.gz",
        "windows/windows-source-preparation.tar.gz",
        "windows/windows-dictionary-snapshots.tar.gz",
    }
    members = {
        f"{platform}/{name}": name
        for platform, names in (
            ("macos", macos_names(version)),
            ("windows", windows_names(version)),
        )
        for name in names
        if not name.endswith((".dmg", ".exe"))
        and ((f"{platform}/{name}" in sources) == (kind == "sources"))
    }
    return dict(sorted(members.items()))


def bundle_guide(version: str, kind: str) -> bytes:
    if kind == "sources":
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
    else:
        text = f"""YomiMado {version} — notices and original verification records

Extract the platform notice archives under macos/ and windows/ to read the
original licences, copyright notices, source credits and component terms.
The other files retain the original platform candidate records, native input
inventory and checksums. No approval flags in these records have been rewritten.
Human installed-app tests and publication approval are recorded separately.

desktop-release-candidate.json binds both installers and these combined archives.
desktop-SHA256SUMS.txt checks all five other downloadable release files.
"""
    return text.encode("utf-8")


def write_bundle(
    target: Path, directories: dict[str, Path], version: str, kind: str
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
        guide = bundle_guide(version, kind)
        member = tarfile.TarInfo("README.txt")
        member.size = len(guide)
        member.mode = 0o644
        archive.addfile(member, io.BytesIO(guide))
        for name, filename in bundle_members(version, kind).items():
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


def verify_bundle(path: Path, version: str, kind: str, inputs: dict) -> None:
    members = bundle_members(version, kind)
    guide = bundle_guide(version, kind)
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
    for kind in ("sources", "notices"):
        write_bundle(
            output / f"YomiMado_{version}_{kind}.tar.gz", directories, version, kind
        )
    record = {
        "layout": LAYOUT,
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
    if layout not in (None, LAYOUT):
        raise ValueError("Unknown combined release layout")
    # Keep the original 17-file v0.1.0 record readable without repackaging it.
    names = (
        public_names(version)
        if layout == LAYOUT
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
    if layout == LAYOUT:
        inputs = expected.get("inputs", {})
        if set(inputs) != macos_names(version) | windows_names(version) or any(
            not re.fullmatch(r"[0-9a-f]{64}", sha) for sha in inputs.values()
        ):
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
                else windows_names(version)
            )
            if candidate.get("assets") != {
                name: inputs[name] for name in candidate_names
            }:
                raise ValueError("Platform candidate input hashes differ")
        for name in (
            f"YomiMado_{version}_aarch64.dmg",
            f"YomiMado_{version}_x64-setup.exe",
        ):
            if inputs[name] != expected["assets"][name]:
                raise ValueError("Combined installer bytes differ from platform inputs")
        for kind in ("sources", "notices"):
            verify_bundle(
                directory / f"YomiMado_{version}_{kind}.tar.gz", version, kind, inputs
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
