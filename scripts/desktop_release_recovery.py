"""Publish only the pinned v0.5.0 candidate after a fresh protected main review.

The original PR-triggered publisher was rejected before any step ran. Preserve
its installers and notes; permit only release-repair changes after that source.
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import zipfile
from pathlib import Path

import desktop_release as release
import release_notes
from release_api import API, request
from windows_release import digest, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "8ff3be2621096a9804cc23ba33902f5aab34da55"
RUN = 39571798373
RUN_HEAD = "98e5ccf6fd546b313f7303d7bdbc11fe70b14e34"
ARTIFACTS = {
    "candidate": {
        "id": 12335661391,
        "name": "verified-desktop-candidate",
        "size": 4267577495,
        "sha256": "89a488eb607d4772149c6ad3f5bbcf1a3d7764204581c2929820dc7155665fb3",
    },
    "notes": {
        "id": 12331803425,
        "name": "release-notes-preview",
        "size": 1110,
        "sha256": "c8b6bff11e669f90d249687914f49ec77a545f25cab766b454cd753d7cf9f93c",
    },
}
INSTALLERS = {
    "YomiMado_0.5.0_aarch64.dmg": "778c865a7b95cc05becdfc6526aa492f0cf6bf41fb72841bc9bc7218e51df1f7",
    "YomiMado_0.5.0_x64-setup.exe": "aa69306dfab65cadf21702e2e6ad537faf725c03af36693a7e58f4be05e6e8c6",
}
REPAIR_FILES = {
    ".github/workflows/release.yml",
    ".github/workflows/desktop-release-resume.yml",
    ".github/workflows/checks.yml",
    "scripts/desktop_release.py",
    "scripts/desktop_release_recovery.py",
    "scripts/macos-ci-release.py",
    "scripts/tests/test_desktop_release.py",
    "scripts/tests/test_desktop_release_recovery.py",
    "docs/release-runbook.md",
    "docs/README.md",
    "docs/development.md",
    "scripts/README.md",
    "docs/desktop-release.md",
    "docs/release-recovery-0.5.0.md",
    "docs/implementation-plan.md",
    "CHANGELOG.md",
}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def verify_repair_scope() -> None:
    release.main_scope()
    if (
        os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or git("rev-parse", "HEAD") != os.environ["GITHUB_SHA"]
    ):
        raise ValueError(
            "Recovery requires a manual run of the checked-out main commit"
        )
    git("merge-base", "--is-ancestor", SOURCE, "HEAD")
    git("diff", "--quiet", "HEAD", "--")
    changed = set(git("diff", "--name-only", "-z", SOURCE, "HEAD").split("\0")) - {""}
    if not changed or not changed.issubset(REPAIR_FILES):
        raise ValueError("Recovery permits only the explicit publication repair files")


def verify_repository() -> None:
    if (
        request(API).get("default_branch") != "main"
        or request(API + "/git/ref/heads/main")["object"]["sha"]
        != os.environ["GITHUB_SHA"]
    ):
        raise ValueError("Recovery main advanced or is not the default branch")
    release.verify_main_rules(request(API + "/rules/branches/main?per_page=100"))
    release.macos.verify_environment(
        request(API + "/environments/desktop-release"),
        request(API + "/environments/desktop-release/deployment-branch-policies"),
    )
    release.verify_main_checks(
        request(
            API
            + f"/commits/{os.environ['GITHUB_SHA']}/check-runs?check_name=gates&filter=latest&per_page=100"
        )
    )


def verify_origin() -> None:
    run = request(API + f"/actions/runs/{RUN}")
    if any(
        run.get(key) != value
        for key, value in {
            "id": RUN,
            "head_sha": RUN_HEAD,
            "head_branch": "release/0.5.0",
            "event": "pull_request",
            "path": ".github/workflows/release.yml",
            "status": "completed",
            "conclusion": "failure",
        }.items()
    ):
        raise ValueError("Original release run identity differs")
    report = request(API + f"/actions/runs/{RUN}/jobs?filter=latest&per_page=100")
    jobs = report.get("jobs", [])
    names = {
        "plan",
        "seed-inputs",
        "Build macOS Apple Silicon",
        "Build Windows 11 x64 CPU installer",
        "verify-transfer",
        "publish",
    }
    if (
        report.get("total_count") != 6
        or len(jobs) != 6
        or {j.get("name") for j in jobs} != names
    ):
        raise ValueError("Original release jobs are missing or ambiguous")
    for job in jobs:
        expected = "failure" if job["name"] == "publish" else "success"
        if job.get("status") != "completed" or job.get("conclusion") != expected:
            raise ValueError("Original build and combined verification must succeed")
        if job["name"] == "publish" and job.get("steps") != []:
            raise ValueError(
                "Original publisher ran steps; investigate partial publication"
            )
    for pinned in ARTIFACTS.values():
        artifact = request(API + f"/actions/artifacts/{pinned['id']}")
        if (
            artifact.get("id") != pinned["id"]
            or artifact.get("name") != pinned["name"]
            or artifact.get("expired") is not False
            or artifact.get("size_in_bytes") != pinned["size"]
            or artifact.get("digest") != "sha256:" + pinned["sha256"]
            or artifact.get("workflow_run", {}).get("id") != RUN
            or artifact.get("workflow_run", {}).get("head_sha") != RUN_HEAD
        ):
            raise ValueError(
                "Pinned recovery artifact identity/digest/retention differs"
            )


def extract_artifact(archive: Path, output: Path, kind: str) -> None:
    pinned = ARTIFACTS[kind]
    if archive.stat().st_size != pinned["size"] or digest(archive) != pinned["sha256"]:
        raise ValueError("Recovery archive size/hash differs from its fixed pin")
    names = (
        release.public_names("0.5.0", True, split_sources=True)
        | {"desktop-release-candidate.json", "desktop-SHA256SUMS.txt"}
        if kind == "candidate"
        else {"notes.json", "notes.md"}
    )
    with zipfile.ZipFile(archive) as source:
        members = source.infolist()
        if (
            len(members) != len(names)
            or {m.filename for m in members} != names
            or any(
                m.is_dir()
                or stat.S_IFMT(m.external_attr >> 16) not in (0, stat.S_IFREG)
                or m.file_size
                >= (release.ASSET_LIMIT if kind == "candidate" else 1024**2)
                for m in members
            )
        ):
            raise ValueError("Recovery archive contains unexpected or unsafe members")
        output.mkdir()
        for member in members:
            with (
                source.open(member) as incoming,
                (output / member.filename).open("xb") as target,
            ):
                shutil.copyfileobj(incoming, target)


def review_files(work: Path) -> dict:
    record = read_json(work / "candidate/desktop-release-candidate.json")
    if (
        record.get("sourceRevision") != SOURCE
        or record.get("version") != "0.5.0"
        or record.get("tag") != "v0.5.0"
        or record.get("prerelease") is not True
        or any(
            record.get("assets", {}).get(name) != sha
            for name, sha in INSTALLERS.items()
        )
    ):
        raise ValueError(
            "Recovery candidate differs from the original v0.5.0 installers"
        )
    release.verify_combined(work / "candidate", record, source_revision=SOURCE)
    prepared = work / "notes/notes.json"
    release_notes.compose(prepared, digest(prepared), record, work / "release-notes.md")
    return record


def prepare(work: Path) -> dict:
    verify_repair_scope()
    verify_repository()
    verify_origin()
    work.mkdir()
    for kind, pinned in ARTIFACTS.items():
        archive = work / f"{kind}.zip"
        with archive.open("xb") as output:
            # gh follows the signed redirect without forwarding the job token.
            subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{release.REPOSITORY}/actions/artifacts/{pinned['id']}/zip",
                ],
                stdout=output,
                check=True,
            )
        extract_artifact(archive, work / kind, kind)
    return review_files(work)


def release_pages() -> list[list[dict]]:
    pages = []
    for page in range(1, 21):
        batch = request(API + f"/releases?per_page=100&page={page}")
        if not isinstance(batch, list) or len(batch) > 100:
            raise ValueError("Invalid release enumeration")
        pages.append(batch)
        if len(batch) < 100:
            return pages
    raise ValueError("Incomplete release enumeration")


def publish(work: Path) -> dict:
    record = prepare(work)
    verify_repository()
    if git(
        "ls-remote", "--tags", "origin", "refs/tags/v0.5.0", "refs/tags/v0.5.0^{}"
    ) or any(
        item.get("tag_name") == "v0.5.0" for page in release_pages() for item in page
    ):
        raise ValueError(
            "v0.5.0 tag/release already exists; investigate before recovery"
        )
    request(API + "/git/refs", "POST", {"ref": "refs/tags/v0.5.0", "sha": SOURCE})
    subprocess.run(
        [
            "gh",
            "release",
            "create",
            "v0.5.0",
            *[str(path) for path in sorted((work / "candidate").iterdir())],
            "--repo",
            release.REPOSITORY,
            "--verify-tag",
            "--target",
            SOURCE,
            "--title",
            "YomiMado v0.5.0",
            "--notes-file",
            str(work / "release-notes.md"),
            "--draft",
            "--prerelease",
        ],
        check=True,
    )
    release_id = release.select_uploaded_release(release_pages(), record)
    endpoint = API + f"/releases/{release_id}"
    report = request(endpoint)
    tag = request(API + "/git/ref/tags/v0.5.0")["object"]
    if (
        report.get("id") != release_id
        or tag.get("sha") != SOURCE
        or tag.get("type") != "commit"
    ):
        raise ValueError("Recovery uploaded draft or tag identity differs")
    release.verify_uploaded(work / "candidate", record, report, source_revision=SOURCE)
    verify_repository()
    final = request(endpoint, "PATCH", {"draft": False})
    if final.get("id") != release_id:
        raise ValueError("Recovery published release ID differs")
    release.verify_uploaded(
        work / "candidate", record, final, draft=False, source_revision=SOURCE
    )
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("review", "publish"))
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "review":
        record = prepare(args.directory)
        message = "Original v0.5.0 candidate and notes verified; fresh owner publication review required."
    else:
        report = publish(args.directory)
        write_json(args.directory / "published-release.json", report)
        record = read_json(args.directory / "candidate/desktop-release-candidate.json")
        message = (
            "Verified original-candidate recovery publication: " + report["html_url"]
        )
    print(message)
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
        stream.write(
            f"\n{message}\n\nOriginal source: `{SOURCE}`; original run: `{RUN}`.\n\n"
        )
        stream.writelines(
            f"- {name}: `{sha}`\n" for name, sha in record["assets"].items()
        )


if __name__ == "__main__":
    main()
