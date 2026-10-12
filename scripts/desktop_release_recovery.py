"""Resume only the retained, tested v0.1.0 draft; never create tags or assets.

The original publisher uploaded all files, then its draft-by-tag lookup failed.
This one-candidate recovery keeps the original source/installer hashes and needs
a new protected owner review. Its main commit may change only release tooling.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import desktop_release as release
from windows_private_draft import API, request
from windows_release import digest, read_json, write_json

ROOT = Path(__file__).parents[1]
SOURCE = "5159473da21c952f1a4dc87c457bba82edf5edde"
RUN = 38201230907
ARTIFACT = 11726850805
ARTIFACT_SHA = "a6eec1b72e614ba45d30e9fe0651bb079b6266df0db5a4871e55bc896a5be91a"
RECORD_SHA = "595b6ef64575c6d45d0e3812a4819afd710afa99e2bbb4be6a1cd577664df42d"
INSTALLERS = {
    "YomiMado_0.1.0_aarch64.dmg": "9d2999ae49b1756d23e62e6b703284e1d5c87898dc187757dfa3d881b8b28977",
    "YomiMado_0.1.0_x64-setup.exe": "a8275246dc07a30f84a2109530bd68c3c0cceeed2556ce27fb09681d3a404602",
}
REPAIR_FILES = {
    ".github/workflows/macos-prerelease.yml",
    ".github/workflows/desktop-release-resume.yml",
    ".github/workflows/desktop-release-checks.yml",
    "scripts/desktop_release.py",
    "scripts/macos-ci-release.py",
    "scripts/desktop_release_recovery.py",
    "scripts/tests/test_desktop_release.py",
    "scripts/tests/test_desktop_release_recovery.py",
    "docs/desktop-release-recovery.md",
}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def verify_repair_scope() -> None:
    release.main_scope()
    if git("rev-parse", "HEAD") != os.environ["GITHUB_SHA"]:
        raise ValueError("Recovery checkout differs from the reviewed main commit")
    git("merge-base", "--is-ancestor", SOURCE, "HEAD")
    git("diff", "--quiet", "HEAD", "--")
    changed = set(git("diff", "--name-only", "-z", SOURCE, "HEAD").split("\0"))
    changed.discard("")
    if not changed or not changed.issubset(REPAIR_FILES):
        raise ValueError("Recovery may change only the explicit release repair files")


def verify_repository() -> None:
    if (
        request(API).get("default_branch") != "main"
        or request(API + "/git/ref/heads/main")["object"]["sha"]
        != os.environ["GITHUB_SHA"]
    ):
        raise ValueError("Recovery requires the current protected main commit")
    release.verify_main_rules(request(API + "/rules/branches/main?per_page=100"))
    release.macos.verify_environment(
        request(API + "/environments/macos-release"),
        request(API + "/environments/macos-release/deployment-branch-policies"),
    )
    tag = request(API + "/git/ref/tags/v0.1.0")["object"]
    if tag.get("sha") != SOURCE or tag.get("type") != "commit":
        raise ValueError("Recovery requires the existing unchanged exact-source tag")


def verify_origin() -> None:
    run = request(API + f"/actions/runs/{RUN}")
    if (
        run.get("head_sha") != SOURCE
        or run.get("head_branch") != "main"
        or run.get("event") != "push"
        or run.get("path") != ".github/workflows/macos-prerelease.yml"
        or run.get("status") != "completed"
        or run.get("conclusion") != "failure"
    ):
        raise ValueError("Recovery build-run identity differs")
    jobs = request(API + f"/actions/runs/{RUN}/jobs?per_page=100")
    names = {
        "plan",
        "seed-inputs",
        "Build macOS Apple Silicon",
        "Build Windows 11 x64 CPU installer",
        "verify-transfer",
        "publish",
    }
    if jobs.get("total_count") != 6 or {j["name"] for j in jobs["jobs"]} != names:
        raise ValueError("Recovery build jobs are missing or ambiguous")
    for job in jobs["jobs"]:
        expected = "failure" if job["name"] == "publish" else "success"
        if job.get("status") != "completed" or job.get("conclusion") != expected:
            raise ValueError(
                "Recovery requires successful original build/transfer gates"
            )
    artifact = request(API + f"/actions/artifacts/{ARTIFACT}")
    if (
        artifact.get("name") != "verified-desktop-candidate"
        or artifact.get("expired") is not False
        or artifact.get("digest") != "sha256:" + ARTIFACT_SHA
        or artifact.get("workflow_run", {}).get("id") != RUN
        or artifact.get("workflow_run", {}).get("head_sha") != SOURCE
    ):
        raise ValueError("Recovery artifact identity/digest/retention differs")


def review_candidate(directory: Path) -> dict:
    verify_repair_scope()
    verify_repository()
    verify_origin()
    path = directory / "desktop-release-candidate.json"
    if digest(path) != RECORD_SHA:
        raise ValueError("Recovery must use the original exact combined record")
    record = read_json(path)
    if (
        record.get("sourceRevision") != SOURCE
        or record.get("version") != "0.1.0"
        or record.get("tag") != "v0.1.0"
        or record.get("prerelease") is not True
        or any(record.get("assets", {}).get(n) != s for n, s in INSTALLERS.items())
    ):
        raise ValueError("Recovery candidate differs from the tested installers")
    release.verify_combined(directory, record, source_revision=SOURCE)
    return record


def publish_existing(directory: Path) -> dict:
    record = review_candidate(directory)
    pages = []
    for page in range(1, 21):
        batch = request(API + f"/releases?per_page=100&page={page}")
        pages.append(batch)
        if len(batch) < 100:
            break
    release_id = release.select_uploaded_release(pages, record)
    endpoint = API + f"/releases/{release_id}"
    # Recheck current main/protections and the fresh draft report immediately
    # before the sole mutation. There is no tag, upload, overwrite or delete path.
    verify_repository()
    report = request(endpoint)
    if report.get("id") != release_id:
        raise ValueError("Recovery draft ID changed")
    release.verify_uploaded(directory, record, report, source_revision=SOURCE)
    final = request(endpoint, "PATCH", {"draft": False})
    if final.get("id") != release_id:
        raise ValueError("Published release ID differs; inspect owner-visible state")
    release.verify_uploaded(
        directory, record, final, draft=False, source_revision=SOURCE
    )
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("review", "publish-existing"))
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "review":
        review_candidate(args.directory)
        message = "Exact original v0.1.0 files verified; new owner publication review required."
    else:
        report = publish_existing(args.directory)
        write_json(Path(os.environ["RUNNER_TEMP"]) / "recovered-release.json", report)
        message = "Verified recovered publication: " + report["html_url"]
    print(message)
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
        stream.write(f"\n{message}\n\nOriginal source: `{SOURCE}`.\n\n")
        stream.write(
            "No installer rebuild, new tag, asset replacement or gate bypass.\n\n"
        )
        stream.writelines(f"- {name}: `{sha}`\n" for name, sha in INSTALLERS.items())


if __name__ == "__main__":
    main()
